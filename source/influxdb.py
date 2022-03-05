# Interface to InfluxDB database
#
# InfluxDB Line Protocol Reference
# https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/

import os
import logging
from time import time
import datetime
from typing import List

from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

from config.configuration import Configuration

from exceptions import FailedInitialization
from urllib3.exceptions import ReadTimeoutError, ConnectTimeoutError, NewConnectionError

from state_engine import get_state_value, set_state
from hash import *


_LOGGER = logging.getLogger("mme")


class InfluxDB:

    _client = None
    _write_api = None
    _query_api = None

    _enable = False
    _url = None
    _token = None
    _bucket = None
    _org = None

    _line_points = []
    _block_size = 500

    _backup_file = 'cached/influxdb.backup'

def influxdb_connect(influxdb_config: Configuration):
    if InfluxDB._client is None:
        influxdb_config = dict(influxdb_config)
        InfluxDB._url = influxdb_config.get('url')
        InfluxDB._token = influxdb_config.get('token')
        InfluxDB._bucket = influxdb_config.get('bucket')
        InfluxDB._org = influxdb_config.get('org')
        InfluxDB._block_size = influxdb_config.get('block_size', 500)
        InfluxDB._enable = influxdb_config.get('enable', False)
        _connect_influxdb_client()

        if not os.path.exists(InfluxDB._backup_file):
            path = os.path.dirname(InfluxDB._backup_file)
            if not os.path.exists(path):
                os.mkdir(path)
            try:
                with open(InfluxDB._backup_file, 'w') as _:
                    pass
            except FileNotFoundError:
                raise FailedInitialization(f"Unable to create InfluxDB backup file {InfluxDB._backup_file}")
        else:
            write_lp_points([])


def _connect_influxdb_client():
    try:
        InfluxDB._client = InfluxDBClient(url=InfluxDB._url, token=InfluxDB._token, org=InfluxDB._org, timeout=500, enable_gzip=True)
        if InfluxDB._client:
            InfluxDB._write_api = InfluxDB._client.write_api(write_options=SYNCHRONOUS)
            InfluxDB._query_api = InfluxDB._client.query_api()
            try:
                InfluxDB._query_api.query(f'from(bucket: "{InfluxDB._bucket}") |> range(start: -1m)')
                _LOGGER.info(f"Connected to the InfluxDB database at {InfluxDB._url}, bucket '{InfluxDB._bucket}'")
            except ApiException as e:
                raise FailedInitialization(f"An exception occurred during InfluxDB query: {e.message}")
            except (NewConnectionError, ConnectTimeoutError, ReadTimeoutError):
                _LOGGER.error(f"Unable to access bucket '{InfluxDB._bucket}' at {InfluxDB._url}")
        else:
            _LOGGER.error(f"Failed to get InfluxDBClient from {InfluxDB._url} (check url, token, and/or organization)")
    except (ApiException, NewConnectionError, ConnectTimeoutError):
        _LOGGER.error(f"Unable to access server at {InfluxDB._url}")


def influxdb_disconnect():
    if len(InfluxDB._line_points) > 0:
        influxdb_write_record(data_points=[], flush=True)
    if InfluxDB._write_api:
        try:
            InfluxDB._write_api.close()
        except ApiException:
            pass
        InfluxDB._write_api = None
    if InfluxDB._client:
        try:
            InfluxDB._client.close()
            _LOGGER.info(f"Disconnected from the InfluxDB database at {InfluxDB._url}")
        except ApiException:
            pass
        InfluxDB._client = None


def write_lp_points(lp_points: List) -> None:
    try:
        if len(lp_points) > 0:
            InfluxDB._write_api.write(bucket=InfluxDB._bucket, record=lp_points, write_precision=WritePrecision.S)
            _LOGGER.info(f"Wrote {len(lp_points)} points to {InfluxDB._url}")
        if os.path.getsize(InfluxDB._backup_file):
            try:
                with open(InfluxDB._backup_file, 'r') as infile:
                    cached_points = list(infile)
                InfluxDB._write_api.write(bucket=InfluxDB._bucket, record=cached_points, write_precision=WritePrecision.S)
                with open(InfluxDB._backup_file, 'w') as _:
                    pass
                _LOGGER.info(f"Wrote {len(cached_points)} cached points from backup file '{InfluxDB._backup_file}' to {InfluxDB._url}")
            except ApiException as e:
                _LOGGER.error(f"Failed to write backup file: {e}")
            except (ReadTimeoutError, ConnectTimeoutError):
                _LOGGER.error(f"Failed to write backup file '{InfluxDB._backup_file}' contents to {InfluxDB._url}")
    except ApiException as e:
        _LOGGER.error(f"InfluxDB ApiException: {e}")
        with open(InfluxDB._backup_file, 'a') as outfile:
            for lp_point in InfluxDB._line_points:
                outfile.write(f"{lp_point}\n")
    except (RuntimeError, ReadTimeoutError, ConnectTimeoutError):
        with open(InfluxDB._backup_file, 'a') as outfile:
            for lp_point in InfluxDB._line_points:
                outfile.write(f"{lp_point}\n")
        _LOGGER.error(f"Wrote {len(InfluxDB._line_points)} points to backup file '{InfluxDB._backup_file}'")


def influxdb_trip(tags: List[Hash], fields: List[Hash], trip_start: Hash) -> None:
    ts_start = get_state_value(trip_start)
    time_tag = datetime.datetime.fromtimestamp(ts_start).strftime('%Y-%m-%dT%H:%M')

    line_protocol = f"trip,session={time_tag}"
    for _, hash in enumerate(tags):
        tag_name, tag_type = get_db_fields(hash)
        if tag_type == 'str':
            line_protocol += ',' + tag_name + '=' + f'"{get_state_value(hash)}"'
        else:
            _LOGGER.warning(f"Only string types allowed as tag values: {field_name}")
    line_protocol += ' '

    for index, hash in enumerate(fields):
        if index >= 1:
            line_protocol += ','
        field_name, field_type = get_db_fields(hash)
        field_value = str(get_state_value(hash))
        if field_type == 'str':
            field_value = f'"{field_value}"'
        line_protocol += field_name + '=' + field_value
        if field_type == 'int':
            line_protocol += 'i'
    line_protocol += f" {ts_start}"
    write_lp_points([line_protocol])
    _LOGGER.info(f"Trip timestamp: {ts_start}")


def influxdb_charging(tags: List[Hash], fields: List[Hash], charge_start: Hash) -> None:
    ts_start = get_state_value(charge_start)
    time_tag = datetime.datetime.fromtimestamp(ts_start).strftime('%Y-%m-%dT%H:%M')

    line_protocol = f"charging,session={time_tag}"
    for _, hash in enumerate(tags):
        tag_name, tag_type = get_db_fields(hash)
        if tag_type == 'str':
            line_protocol += ',' + tag_name + '=' + f'"{get_state_value(hash)}"'
        else:
            _LOGGER.warning(f"Only string types allowed as tag values: {field_name}")
    line_protocol += ' '

    for index, hash in enumerate(fields):
        if index >= 1:
            line_protocol += ','
        field_name, field_type = get_db_fields(hash)
        field_value = str(get_state_value(hash))
        if field_type == 'str':
            field_value = f'"{field_value}"'
        line_protocol += field_name + '=' + field_value
        if field_type == 'int':
            line_protocol += 'i'
    line_protocol += f" {ts_start}"
    write_lp_points([line_protocol])
    _LOGGER.info(f"Charging session timestamp: {ts_start}")


def influxdb_write_record(data_points: List[dict], flush=False) -> None:
    lp_points = []
    ts = int(time())
    for data_point in data_points:
        arb_id = data_point.get('arbitration_id')
        did_id = data_point.get('did_id')
        did_name = data_point.get('name')
        value = data_point.get('value')
        line_protocol = f"dids,arb_id={arb_id:04X},did_id={did_id:04X} {did_name}="
        if hash := get_hash(f"{arb_id:04X}:{did_id:04X}:{did_name}"):
            _, field_type = get_db_fields(hash)
            if field_type == 'str':
                value = f'"{value}"'
            line_protocol += str(value)
            if field_type == 'int':
                line_protocol += 'i'
            if field_type == 'bool':
                line_protocol += ''
            line_protocol += f" {ts}"
            lp_points.append(line_protocol)
            InfluxDB._line_points += lp_points
        else:
            _LOGGER.error(f"Can't find hash for: {arb_id:04X}:{did_id:04X}:{did_name}")

    if len(InfluxDB._line_points) >= InfluxDB._block_size or flush == True:
        if len(InfluxDB._line_points) > 0:
            write_lp_points(InfluxDB._line_points)
            InfluxDB._line_points = []


if __name__ == '__main__':
    set_state(Hash.Vehicle, 'Greta')
    set_state(Hash.CS_ChargerType, 'AC')
    set_state(Hash.CS_TimeStart, 0)
    set_state(Hash.CS_TimeEnd, 20000)
    set_state(Hash.CS_StartSoCD, 60)
    set_state(Hash.CS_EndSoCD, 80)
    set_state(Hash.CS_StartEtE, 30000)
    set_state(Hash.CS_EndEte, 50000)
    set_state(Hash.CS_Odometer, 10000)
    set_state(Hash.CS_Latitude, 42.0)
    set_state(Hash.CS_Longitude, -76.0)
    set_state(Hash.CS_MaxInputPower, 10000)
    set_state(Hash.CS_WhAdded, 25000)
    set_state(Hash.CS_WhUsed, 30000)
    set_state(Hash.CS_ChargingEfficiency, 0.91)

    tag_list = [Hash.CS_ChargerType, Hash.Vehicle]
    field_list = [
        Hash.CS_TimeStart, Hash.CS_TimeEnd,
        Hash.CS_Latitude, Hash.CS_Longitude, Hash.CS_Odometer,
        Hash.CS_StartSoCD, Hash.CS_EndSoCD, Hash.CS_StartEtE, Hash.CS_EndEte,
        Hash.CS_WhAdded, Hash.CS_WhUsed, Hash.CS_ChargingEfficiency, Hash.CS_MaxInputPower,
    ]
    influxdb_charging(tag_list=tag_list, field_list=field_list, charge_start=Hash.CS_TimeStart)
    pass