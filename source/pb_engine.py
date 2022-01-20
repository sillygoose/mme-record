import os
from threading import Thread
from queue import Full

import logging
from time import sleep
import json

from typing import List

from module_manager import ModuleManager
from config.configuration import Configuration

from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class PlaybackEngine:

    def __init__(self, config: Configuration, module_event_queues: dict, module_manager: ModuleManager) -> None:
        playback_config = dict(config)
        self._module_manager = module_manager
        self._module_event_queues = module_event_queues
        source_path = playback_config.get('source_path')
        source_file = playback_config.get('source_file')
        self._playback_files_master = self._get_playback_files(source_path=source_path, source_file=source_file)
        self._playback_files = self._playback_files_master.copy()
        self._start_at = playback_config.get('start_at', 0)
        if self._start_at < 0:
            raise FailedInitialization(f"'start_at' option must be a non-negative integer")
        speed = playback_config.get('speed', 1.0)
        if speed < 1:
            raise FailedInitialization(f"'speed' option must be a floating point number greater than 1.0")
        elif speed > 1.25:
            _LOGGER.info(f"Playback speed is {speed:.0f}x real-time")
        self._speed = 1.0 / speed

        self._loop = config.get('loop', False)
        self._exit_requested = False
        self._currrent_position = None
        self._current_playback = None
        self._thread = None

    def start(self) -> Thread:
        self._exit_requested = False
        self._playback_time = None
        self._thread = Thread(target=self._playback_engine, name='playback_engine')
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()

    def _playback_engine(self) -> None:
        try:
            while self._exit_requested == False:
                event = self._next_event()
                if event is None:
                    return
                event_time = event.get('time')
                if self._playback_time < event_time:
                    sleep_for = (event_time - self._playback_time)
                    if sleep_for > 0:
                        if sleep_for > 5:
                            _LOGGER.info(f"At time {self._playback_time:.02f}, sleeping {sleep_for:.0f} seconds, skipping ahead")
                            sleep_for = 1
                        sleep(sleep_for * self._speed)
                self._playback_time = event_time

                arbitration_id = event.get('arbitration_id')
                module_name = self._module_manager.module_name(arbitration_id)
                module_event_queue = self._module_event_queues.get(module_name)
                if module_event_queue:
                    try:
                        module_event_queue.put(event, block=False, timeout=2)
                    except Full:
                        _LOGGER.error(f"Queue {module_name}/{arbitration_id:04X} is full")
                        return
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def _zoom_ahead(self, start_at: int) -> None:
        event_time = 0
        while event_time < start_at:
            if self._currrent_position is None or self._currrent_position == len(self._current_playback):
                next_file = self._next_file()
                if next_file is None:
                    raise RuntimeError(f"'start_at' option is larger than the largest playback file - nothing to playback")
            event = self._current_playback[self._currrent_position]
            event_time = event.get('time')
            self._currrent_position += 1
        self._playback_time = event_time
        _LOGGER.info(f"Starting at time {event_time} in file '{next_file}'")

    def _next_event(self) -> dict:
        if self._start_at > 0:
            self._zoom_ahead(self._start_at)
            self._start_at = 0
        if self._currrent_position is None or self._currrent_position == len(self._current_playback):
            next_file = self._next_file()
            if next_file is None:
                return None
        event = self._current_playback[self._currrent_position]
        if self._playback_time is None:
            self._playback_time = event.get('time')
        self._currrent_position += 1
        return event

    def _next_file(self) -> str:
        if self._playback_files == []:
            if self._loop == False:
                return None
            self._playback_files = self._playback_files_master.copy()
        next_file = self._playback_files.pop(0)
        self._load_playback(file=next_file)
        self._currrent_position = 0
        return next_file

    def _decode_event(self, event: dict) -> str:
        module_name = self._module_manager.module_name(event.get('arbitration_id'))
        event['name'] = module_name
        event['payload'] = bytearray(event['payload'])
        return str(event)

    def _get_playback_files(self, source_path: str, source_file: str) -> List:
        playback_files = []
        count = 0
        find_file = f"{source_path}/{source_file}_{count:03d}.json"
        if not os.path.exists(find_file):
            raise FailedInitialization(f"Can't find the playback file '{find_file}'")
        while True:
            if not os.path.exists(find_file):
                break
            playback_files.append(find_file)
            count += 1
            find_file = f"{source_path}/{source_file}_{count:03d}.json"
        return playback_files

    def _load_playback(self, file: str) -> None:
        with open(file) as infile:
            try:
                self._current_playback = json.load(infile)
                _LOGGER.info(f"Loaded playback file '{file}'")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        self._currrent_position = 0

    def _dump_playback(self, file: str, playback: dict) -> None:
        json_playback = json.dumps(playback, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_playback)
