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
            except (ApiException, NewConnectionError, ConnectTimeoutError, ReadTimeoutError):
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
            except (ApiException, ReadTimeoutError, ConnectTimeoutError):
                _LOGGER.error(f"Failed to write backup file '{InfluxDB._backup_file}' contents to {InfluxDB._url}")
    except (RuntimeError, ApiException, ReadTimeoutError, ConnectTimeoutError):
        with open(InfluxDB._backup_file, 'a') as outfile:
            for lp_point in InfluxDB._line_points:
                outfile.write(f"{lp_point}\n")
        _LOGGER.error(f"Wrote {len(InfluxDB._line_points)} points to backup file '{InfluxDB._backup_file}'")


def influxdb_charging_session(session: dict, vehicle: str) -> None:
    """
            charging_session = {
                'type':             charger_type,
                'time':             starting_time,
                'duration':         duration_seconds,
                'location':         {'latitude': latitude, 'longitude': longitude},
                'odometer':         odometer,
                'soc':              {'starting': starting_soc, 'ending': ending_soc},
                'socd':             {'starting': starting_socd, 'ending': ending_socd},
                'ete':              {'starting': starting_ete, 'ending': ending_ete},
                'kwh_added':        kwh_added,
                'kwh_used':         kwh_used,
                'efficiency':       charging_efficiency,
                'max_power':        max_input_power,
            }
    """
    charging_session = []
    charger_type = session.get('type')
    ts = session.get('time')
    duration = session.get('duration')
    end_ts = ts + duration
    latitude = session.get('location').get('latitude')
    longitude = session.get('location').get('longitude')
    odometer = session.get('odometer')
    starting_soc = session.get('soc').get('starting')
    ending_soc = session.get('soc').get('ending')
    starting_socd = session.get('socd').get('starting')
    ending_socd = session.get('socd').get('ending')
    starting_ete = session.get('ete').get('starting')
    ending_ete = session.get('ete').get('ending')
    kwh_added = session.get('kwh_added')
    kwh_used = session.get('kwh_used')
    efficiency = session.get('efficiency')
    max_input_power = session.get('max_power')
    tag_value = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M')
    charging_session.append(
        f"charging" \
        f",vehicle={vehicle},session={tag_value},session={charger_type} " \
        f"odometer={odometer},latitude={latitude},longitude={longitude},duration={duration}," \
        f"soc_begin={starting_soc},soc_end={ending_soc},socd_begin={starting_socd},socd_end={ending_socd}," \
        f"ete_begin={starting_ete},ete_end={ending_ete},max_power={max_input_power}," \
        f"kwh_added={kwh_added},kwh_used={kwh_used},efficiency={efficiency} {ts}")
    charging_session.append(
        f"charging" \
        f",vehicle={vehicle},session={tag_value},session={charger_type} " \
        f"odometer={odometer},latitude={latitude},longitude={longitude},duration={duration}," \
        f"soc_begin=0.0,soc_end=0.0,socd_begin=0.0,socd_end=0.0," \
        f"ete_begin=0.0,ete_end=0.0,max_power=0.0," \
        f"kwh_added=0.0,kwh_used=0.0,efficiency=0.0 {end_ts}")
    write_lp_points(charging_session)


def influxdb_write_record(data_points: List[dict], flush=False) -> None:
    lp_points = []
    ts = int(time())
    for data_point in data_points:
        arb_id = data_point.get('arbitration_id')
        did_id = data_point.get('did_id')
        did_name = data_point.get('name')

        v_type = ''
        value = data_point.get('value')
        if isinstance(value, float):
            v_type = ''
        elif isinstance(value, bool):
            v_type = ''
        elif isinstance(value, int):
            v_type = 'i'
        lp_points.append(f"dids,arb_id={arb_id:04X},did_id={did_id:04X} {did_name}={value}{v_type} {ts}")
    InfluxDB._line_points += lp_points

    if len(InfluxDB._line_points) >= InfluxDB._block_size or flush == True:
        if len(InfluxDB._line_points) > 0:
            write_lp_points(InfluxDB._line_points)
            InfluxDB._line_points = []
