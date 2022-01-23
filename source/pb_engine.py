from threading import Thread

import logging
from time import sleep
import json

from module_manager import ModuleManager
from config.configuration import Configuration

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


class PlaybackEngine:

    def __init__(self, config: Configuration, active_modules: dict, module_manager: ModuleManager) -> None:
        playback_config = dict(config)
        self._active_modules = active_modules
        self._module_manager = module_manager
        self._filename = f"{playback_config.get('source_path')}/{playback_config.get('source_file')}.json"
        self._speedup = playback_config.get('speedup', True)
        self._exit_requested = False
        self._currrent_position = None
        self._playback = None
        self._playback_alert_time = self._playback_time = None
        self._thread = None

    def start(self) -> Thread:
        self._exit_requested = False
        self._load_playback()
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
                if (event := self._next_event()) is None:
                    _LOGGER.debug("No more events to process")
                    sleep(10)
                    return
                if (sleep_for := event.get('time') - self._playback_time) > 0:
                    sleep_for = 0.5 if self._speedup and sleep_for > 1.0 else sleep_for
                    sleep(sleep_for)
                self._playback_time = event.get('time')

                if self._playback_time - self._playback_alert_time > 300:
                    _LOGGER.info(f"5 minutes simulated time passed: {int(self._playback_time)}")
                    self._playback_alert_time = self._playback_time

                arbitration_id = event.get('arbitration_id')
                module_name = self._module_manager.module_name(arbitration_id)
                if module := self._active_modules.get(module_name):
                    module.process_event(event)
                else:
                    _LOGGER.debug(f"what? {module_name}")
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def _next_event(self) -> dict:
        if self._currrent_position is None or self._currrent_position == len(self._playback):
            return None
        event = self._playback[self._currrent_position]
        if self._playback_time is None:
            self._playback_alert_time = self._playback_time = event.get('time')
        self._currrent_position += 1
        return event

    def _load_playback(self) -> None:
        with open(self._filename) as infile:
            try:
                self._playback = json.load(infile)
                self._currrent_position = 0
                _LOGGER.info(f"Loaded playback file '{self._filename}'")
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{self._filename}' at line {e.lineno}")
