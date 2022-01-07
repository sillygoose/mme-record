import sys
import os
import threading
from queue import Queue, Full

import logging
from time import time, sleep
import json

from typing import List

import module
from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class PlaybackEngine:

    def __init__(self, config: dict, queues: dict) -> None:
        self._config = config
        self._queues = queues
        self._playback_files = self._get_playback_files(config.get('source_dir'), config.get('source_file'))
        self._start_at = config.get('start_at', 0)
        speed = config.get('speed', 1.0)
        if speed < 1:
            raise FailedInitialization(f"'speed' option must be a value greater than 1.0")
        self._speed = 1.0 / speed 
        self._exit_requested = False
        self._time_zero = int(time())
        self._currrent_position = None
        self._current_playback = None

    def _get_playback_files(self, source_dir: str, source_file: str) -> List:
        playback_files = []
        count = 0
        find_file = f"{source_dir}/{source_file}_{count:03d}.json"
        while True:
            if not os.path.exists(find_file):
                break
            playback_files.append(find_file)
            count += 1
            find_file = f"{source_dir}/{source_file}_{count:03d}.json"
        return playback_files

    def start(self) -> None:
        self._exit_requested = False
        self._playback_time = 0
        """
        if self._start_at > 0:
            offset = 0
            for event in self._playback:
                if event.get('time') < self._start_at:
                    offset += 1
                    continue
                break
            self._currrent_playback = offset
            self._time_zero -= event.get('time')
        """
        self._thread = threading.Thread(target=self._event_task, name='playback')
        self._thread.start()
        self._thread.join()

    def _event_task(self) -> None:
        try:
            while self._exit_requested == False:
                event = self._next_event()
                if event is None:
                    return
                event_time = event.get('time')
                if self._playback_time < event_time:
                    sleep_for = (event_time - self._playback_time) * self._speed
                    if sleep_for > 0:
                        if sleep_for > 3:
                            _LOGGER.info(f"sleeping for {sleep_for:.1f} seconds")
                        sleep(sleep_for)
                self._playback_time = event_time

                arbitration_id = event.get('arbitration_id')
                name = module.module_name(arbitration_id)
                destination = self._queues.get(name)
                if destination:
                    try:
                        _LOGGER.debug(f"Queuing event {event} on queue {name}")
                        destination.put(event, block=False, timeout=2)
                        #print(f"{current_time:.02f}: {self._decode_event(event)}")
                    except Full:
                        _LOGGER.error(f"Queue {name}/{arbitration_id:04X} is full")
                        return
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def stop(self) -> None:
        self._exit_requested = True
        if self._thread.is_alive():
            self._thread.join()

    def _next_event(self) -> dict:
        if self._currrent_position is None or self._currrent_position == len(self._current_playback):
            if self._playback_files == []:
                return
            next_file = self._playback_files.pop(0)
            self._load_playback(file=next_file)
        event = self._current_playback[self._currrent_position]
        self._currrent_position += 1
        return event

    def _decode_event(self, event: dict) -> str:
        module_name = module.module_name(event.get('arbitration_id'))
        event['id'] = module_name
        event['payload'] = bytearray(event['payload'])
        return str(event)

    def _load_playback(self, file: str) -> None:
        with open(file) as infile:
            try:
                self._current_playback = json.load(infile)
                _LOGGER.info(f"Loaded playback file '{file}'")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        self._currrent_position = 0                

    def _dump_playback(self, file: str, playback: dict) -> None:
        json_playback = json.dumps(playback, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_playback)


