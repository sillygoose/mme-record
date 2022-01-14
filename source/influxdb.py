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
        self._block_size = influxdb_config.get('block_size', 100)
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

    def write_record(self, data_points: List[dict], flush=False) -> None:
        if self._client:
            lp_points = []
            ts = int(time())
            for data_point in data_points:
                arbitration_id = data_point.get('arbitration_id')
                did_id = data_point.get('did_id')
                name = data_point.get('name')
                value = data_point.get('value')
                lp_points.append(f"{name},aid={arbitration_id:04X},did={did_id:04X} state={value} {ts}")
            self._line_points += lp_points

            if len(self._line_points) >= self._block_size or flush == True:
                try:
                    self._write_api.write(bucket=self._bucket, record=self._line_points, write_precision=WritePrecision.S)
                    _LOGGER.info(f"Wrote {len(self._line_points)} data points to {self._url}")
                    self._line_points = []
                except Exception as e:
                    _LOGGER.error(f"Database write() call failed in write_record(): {e}")
