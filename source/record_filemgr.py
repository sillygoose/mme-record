import logging
from threading import Thread
from time import time, sleep
import json

from typing import List


_LOGGER = logging.getLogger('mme')


class RecordFileManager:

    def __init__(self, config: dict) -> None:
        self._config = config
        self._data_points = []
        self._file_writes = config.get('file_writes', 200)
        self._dest_path = config.get('dest_path', None)
        self._dest_file = config.get('dest_file', None)
        self._file_count = 0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self._write_file()

    def put(self, data_point: dict) -> None:
        self._data_points.append(data_point)
        if len(self._data_points) >= self._file_writes:
            self._write_file()

    def _write_file(self) -> None:
        if len(self._data_points) > 0:
            filename = f"{self._dest_path}/{self._dest_file}_{self._file_count:03d}.json"
            json_data = json.dumps(self._data_points, indent = 4, sort_keys=False)
            with open(filename, "w") as outfile:
                outfile.write(json_data)
            _LOGGER.info(f"Wrote output file '{filename}'")
            self._file_count += 1
            self._data_points = []
