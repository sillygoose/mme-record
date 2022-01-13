# Interface to InfluxDB database
#
# InfluxDB Line Protocol Reference
# https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/

import logging

from influxdb_client import InfluxDBClient, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from config.configuration import Configuration
from codec_manager import *

from exceptions import FailedInitialization


_LOGGER = logging.getLogger("mme")


class InfluxDB:
    def __init__(self, influxdb_config: Configuration, codec_manager: CodecManager):
        self._codec_manager = codec_manager
        self._client = None
        self._write_api = None
        self._query_api = None
        self._line_points = []
        self._enable = influxdb_config.enable
        self._url = influxdb_config.url
        self._token = influxdb_config.token
        self._bucket = influxdb_config.bucket
        self._org = influxdb_config.org
        self._test_influxdb()

    def _test_influxdb(self) -> None:
        if not self._enable:
            _LOGGER.debug(f"The influxdb2 'enable' option must be true to use InfluxDB")
            return
        try:
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
            except Exception:
                raise FailedInitialization(f"Unable to access bucket '{self._bucket}' at {self._url}")

        except Exception as e:
            FailedInitialization(f"{e}")

    def start(self):
        pass

    def stop(self):
        if self._write_api:
            self._write_api.close()
            self._write_api = None
        if self._client:
            self._client.close()
            self._client = None

    def write_record(self, data_point: dict) -> None:
        lp_points = []
        if data_point.get('type', None) is None:
            did_id = data_point.get('did_id')
            ts = int(data_point.get('time'))
            codec = self._codec_manager.codec(did_id)
            decoded_playload = codec.decode(None, bytearray(data_point.get('payload')))
            arbitration_id = data_point.get('arbitration_id')
            states = decoded_playload.get('states')
            for state in states:
                for k, v in state.items():
                    # myMeasurement,tag1=value1,tag2=value2 fieldKey="fieldValue" 1556813561098000000
                    lp_points.append(f"{k},aid={arbitration_id:04X},did={did_id:04X} state={v} {ts}")
        try:
            self._write_api.write(bucket=self._bucket, record=lp_points, write_precision=WritePrecision.S)
        except Exception as e:
            _LOGGER.error(f"Database write() call failed in write_points(): {e}")
