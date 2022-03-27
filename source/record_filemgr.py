import logging
import os
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
        _LOGGER.info(f"Writing to state file '{self._filename}'")

    def start(self) -> None:
        self._open()

    def stop(self) -> None:
        self._close()

    def _open(self) -> None:
        with open(self._filename, 'w') as outfile:
            outfile.write('[\n')
            self._writes = 0

    def _close(self) -> None:
        with open(self._filename, 'a') as outfile:
            self._write_file()
            outfile.write('\n]')

    def flush(self, rename_to: str = None) -> None:
        self._write_file()
        self._close()
        if rename_to:
            flushed_filename = f"{self._dest_path}/{rename_to}.json"
            os.rename(self._filename, flushed_filename)
        self._open()
        _LOGGER.info(f"Flushed output file and renamed to '{flushed_filename}'" if rename_to else f"Flushed output file '{self._filename}'")

    def write_record(self, data_point: dict) -> None:
        if self._file_writes > 0 :
            self._data_points.append(data_point)
            if len(self._data_points) >= self._file_writes:
                self._write_file()

    def _write_file(self) -> None:
        if len(self._data_points) > 0:
            try:
                json_data = json.dumps(self._data_points, indent = 4, sort_keys=False)[2:-2]
                with open(self._filename, 'a') as outfile:
                    if self._writes > 0:
                        outfile.write(',\n')
                    outfile.write(json_data)
                _LOGGER.info(f"Wrote {len(self._data_points)} data points to output file '{self._filename}'")
                self._writes += 1
                self._data_points = []
            except TypeError as e:
                _LOGGER.error(f"Error converting to JSON: {e}")
