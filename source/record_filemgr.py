import logging
import json

from config.configuration import Configuration


_LOGGER = logging.getLogger('mme')


class RecordFileManager:

    def __init__(self, config: Configuration) -> None:
        config_record = dict(config)
        self._data_points = []
        self._file_writes = config_record.get('file_writes', 200)
        self._dest_path = config_record.get('dest_path', None)
        self._dest_file = config_record.get('dest_file', None)
        self._filename = f"{self._dest_path}/{self._dest_file}.json"

    def start(self) -> None:
        if self._file_writes > 0 :
            self._open()

    def stop(self) -> None:
        if self._file_writes > 0 :
            self._close()

    def _open(self) -> None:
        with open(self._filename, 'w') as outfile:
            outfile.write('[\n')
            self._writes = 0

    def _close(self) -> None:
        with open(self._filename, 'a') as outfile:
            self._write_file()
            outfile.write('\n]')

    def write_record(self, data_point: dict) -> None:
        if self._file_writes > 0 :
            self._data_points.append(data_point)
            if len(self._data_points) >= self._file_writes:
                self._write_file()

    def _write_file(self) -> None:
        if len(self._data_points) > 0:
            json_data = json.dumps(self._data_points, indent = 4, sort_keys=False)[2:-2]
            with open(self._filename, 'a') as outfile:
                if self._writes > 0:
                    outfile.write(',\n')
                outfile.write(json_data)
            _LOGGER.info(f"Wrote {len(self._data_points)} data points to output file '{self._filename}'")
            self._writes += 1
            self._data_points = []
