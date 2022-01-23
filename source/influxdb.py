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
    def __init__(self, influxdb_config: Configuration):
        self._client = None
        self._write_api = None
        self._query_api = None
        self._line_points = []
        influxdb_config = dict(influxdb_config)
        self._enable = influxdb_config.get('enable')
        self._url = influxdb_config.get('url')
        self._token = influxdb_config.get('token')
        self._bucket = influxdb_config.get('bucket')
        self._org = influxdb_config.get('org')
        self._block_size = influxdb_config.get('block_size', 500)
        self._test_influxdb()

    def _test_influxdb(self) -> None:
        if not self._enable:
            _LOGGER.debug(f"The influxdb2 'enable' option must be true to use InfluxDB")
            return

        self._client = InfluxDBClient(url=self._url, token=self._token, org=self._org)
        if not self._client:
            raise FailedInitialization(f"Failed to get InfluxDBClient from {self._url} (check url, token, and/or organization)")

        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        if not self._write_api:
            raise FailedInitialization(f"Failed to get client write_api() object from {self._url}")

        query_api = self._client.query_api()
        if not query_api:
            raise FailedInitialization(f"Failed to get client query_api() object from {self._url}")

        try:
            query_api.query(f'from(bucket: "{self._bucket}") |> range(start: -1m)')
            _LOGGER.info(f"Connected to the InfluxDB database at {self._url}, bucket '{self._bucket}'")
        except ApiException:
            raise FailedInitialization(f"Unable to access bucket '{self._bucket}' at {self._url}")

    def start(self):
        pass

    def stop(self):
        if len(self._line_points) > 0:
            self.write_record(data_points=[], flush=True)
        if self._write_api:
            self._write_api.close()
            self._write_api = None
        if self._client:
            self._client.close()
            self._client = None

    def charging_session(self, session: dict) -> None:
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
            }
        """
        if self._client:
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
            charging_session.append(f"charging,odometer={odometer},latitude={latitude},longitude={longitude},duration={duration}i,soc_begin={starting_soc},soc_end={ending_soc},socd_begin={starting_socd},socd_end={ending_socd},ete_begin={starting_ete},ete_end={ending_ete} kwh_added={kwh_added} {ts}")
            try:
                self._write_api.write(bucket=self._bucket, record=charging_session, write_precision=WritePrecision.S)
            except ApiException as e:
                raise RuntimeError(f"InfluxDB client unable to write to '{self._bucket}' at {self._url}: {e.reason}")

    def write_record(self, data_points: List[dict], flush=False) -> None:
        if self._client:
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
            self._line_points += lp_points

            if len(self._line_points) >= self._block_size or flush == True:
                if len(self._line_points) > 0:
                    try:
                        self._write_api.write(bucket=self._bucket, record=self._line_points, write_precision=WritePrecision.S)
                        _LOGGER.info(f"Wrote {len(self._line_points)} data points to {self._url}")
                        self._line_points = []
                    except ApiException as e:
                        raise RuntimeError(f"InfluxDB client unable to write to '{self._bucket}' at {self._url}: {e.reason}")
