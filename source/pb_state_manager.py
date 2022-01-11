import logging
from threading import Thread
from queue import Queue
from enum import Enum, unique

from typing import List

from codec_manager import CodecManager
from state_manager import StateManager

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


@unique
class PlaybackStateDID(Enum):
        KeyState = 0x411F


class PlaybackStateManager:

    def __init__(self, config: dict, state_queue: Queue) -> None:
        self._config = config
        self._codec_manager = CodecManager(config=self._config)
        self._exit_requested = False
        self._state_queue = state_queue
        self._state = StateManager.VehicleState.Unknown

    def start(self) -> List[Thread]:
        self._exit_requested = False
        self._state_thread = Thread(target=self._update_state, name='state_manager')
        self._state_thread.start()
        return [self._state_thread]

    def stop(self) -> None:
        self._exit_requested = True
        if self._state_thread.is_alive():
            self._state_thread.join()

    def state(self) -> StateManager.VehicleState:
        return self._state

    def _update_state(self) -> None:
        try:
            while self._exit_requested == False:
                state_change = self._state_queue.get()
                _LOGGER.debug(f"New state change: {state_change}")
                did_id = state_change.get('did_id', None)
                if did_id:
                    try:
                        state_did = PlaybackStateDID(did_id)
                        codec = self._codec_manager.codec(did_id)
                        if codec:
                            payload = state_change.get('payload')
                            decoded = codec.decode(None, payload)
                            if state_did == PlaybackStateDID.KeyState:
                                states = decoded.get('states')
                                value = states[0].get('key_state', None)
                                if value:
                                    if value == 0:
                                        self._state = StateManager.VehicleState.Off
                                    elif value == 3:
                                        self._state = StateManager.VehicleState.On
                                    elif value == 4:
                                        self._state = StateManager.VehicleState.Starting
                                    elif value == 5:
                                        self._state = StateManager.VehicleState.Sleeping
                                    _LOGGER.info(decoded.get('decoded'))
                    except ValueError:
                        pass
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
