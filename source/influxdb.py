# Interface to InfluxDB database
#
# InfluxDB Line Protocol Reference
# https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/

import logging
from time import time
from typing import List

from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

from config.configuration import Configuration

from exceptions import FailedInitialization


_LOGGER = logging.getLogger("mme")


class InfluxDB:

    _client = None

    _url = None
    _token = None
    _bucket = None
    _org = None

    _write_api = None
    _query_api = None
    _line_points = []

    _block_size = 500


def influxdb_connect(influxdb_config: Configuration):
    if InfluxDB._client is None:
        influxdb_config = dict(influxdb_config)
        InfluxDB._url = influxdb_config.get('url')
        InfluxDB._token = influxdb_config.get('token')
        InfluxDB._bucket = influxdb_config.get('bucket')
        InfluxDB._org = influxdb_config.get('org')
        InfluxDB._block_size = influxdb_config.get('block_size', 500)
        if influxdb_config.get('enable', False) == False:
            raise FailedInitialization(f"The influxdb2 'enable' option must be true to use InfluxDB")

        InfluxDB._client = InfluxDBClient(url=InfluxDB._url, token=InfluxDB._token, org=InfluxDB._org)
        if not InfluxDB._client:
            raise FailedInitialization(f"Failed to get InfluxDBClient from {InfluxDB._url} (check url, token, and/or organization)")
        InfluxDB._write_api = InfluxDB._client.write_api(write_options=SYNCHRONOUS)
        if not InfluxDB._write_api:
            raise FailedInitialization(f"Failed to get client write_api() object from {InfluxDB._url}")
        InfluxDB._query_api = InfluxDB._client.query_api()
        if not InfluxDB._query_api:
            raise FailedInitialization(f"Failed to get client query_api() object from {InfluxDB._url}")
        try:
            InfluxDB._query_api.query(f'from(bucket: "{InfluxDB._bucket}") |> range(start: -1m)')
            _LOGGER.info(f"Connected to the InfluxDB database at {InfluxDB._url}, bucket '{InfluxDB._bucket}'")
        except ApiException:
            raise FailedInitialization(f"Unable to access bucket '{InfluxDB._bucket}' at {InfluxDB._url}")


def influxdb_disconnect():
    if len(InfluxDB._line_points) > 0:
        influxdb_write_record(data_points=[], flush=True)
    if InfluxDB._write_api:
        InfluxDB._write_api.close()
        InfluxDB._write_api = None
    if InfluxDB._client:
        InfluxDB._client.close()
        InfluxDB._client = None
    _LOGGER.info(f"Disconnected from the InfluxDB database at {InfluxDB._url}")


def influxdb_charging_session(session: dict) -> None:
    """
            charging_session = {
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
            }
    """
    if InfluxDB._client:
        charging_session = []
        ts = session.get('time')
        duration = session.get('duration')
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
        charging_session.append(
            f"charging,odometer={odometer},latitude={latitude},longitude={longitude},duration={duration}i," \
            f"soc_begin={starting_soc},soc_end={ending_soc},socd_begin={starting_socd},socd_end={ending_socd}," \
            f"ete_begin={starting_ete},ete_end={ending_ete},kwh_used={kwh_used},efficiency={efficiency} " \
            f"kwh_added={kwh_added} {ts}")
        try:
            InfluxDB._write_api.write(bucket=InfluxDB._bucket, record=charging_session, write_precision=WritePrecision.S)
        except ApiException as e:
            raise RuntimeError(f"InfluxDB client unable to write to '{InfluxDB._bucket}' at {InfluxDB._url}: {e.reason}")


def influxdb_write_record(data_points: List[dict], flush=False) -> None:
    if InfluxDB._client:
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
                try:
                    InfluxDB._write_api.write(bucket=InfluxDB._bucket, record=InfluxDB._line_points, write_precision=WritePrecision.S)
                    _LOGGER.info(f"Wrote {len(InfluxDB._line_points)} data points to {InfluxDB._url}")
                    InfluxDB._line_points = []
                except ApiException as e:
                    raise RuntimeError(f"InfluxDB client unable to write to '{InfluxDB._bucket}' at {InfluxDB._url}: {e.reason}")
