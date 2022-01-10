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
        self._file_writes = config.get('file_writes', 120)
        self._last_saved = int(time())
        self._dest_path = config.get('dest_path', None)
        self._dest_file = config.get('dest_file', None)
        self._file_count = 0
        self._exit_requested = False

    def start(self) -> Thread:
        self._exit_requested = False
        self._thread = Thread(target=self._file_manager_task, name='file_manager')
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()
        self._write_file()

    def put(self, data_point: dict) -> None:
        self._data_points.append(data_point)

    def _write_file(self) -> None:
        full_filename = f"{self._dest_path}/{self._dest_file}_{self._file_count:03d}.json"
        json_data = json.dumps(self._data_points, indent = 4, sort_keys=False)
        with open(full_filename, "w") as outfile:
            outfile.write(json_data)
        self._file_count += 1
        self._data_points = []

    def _file_manager_task(self) -> None:
        try:
            while self._exit_requested == False:
                slept_for = 0
                while slept_for < self._file_writes:
                    if self._exit_requested == True:
                        return
                    sleep(0.5)
                    slept_for += 0.5
                self._write_file()
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
