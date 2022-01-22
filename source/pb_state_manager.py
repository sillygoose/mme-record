import logging
from threading import Thread
from queue import Queue
from enum import Enum, unique

from codec_manager import CodecManager
from state_manager import VehicleState

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


class PlaybackStateManager:

    def __init__(self, state_queue: Queue) -> None:
        self._state_queue = state_queue
        self._codec_manager = CodecManager()
        self._state = VehicleState.Unknown
        self._exit_requested = False

    def start(self) -> None:
        self._exit_requested = False
        self._state_thread = Thread(target=self._update_state, name='state_manager')
        self._state_thread.start()

    def stop(self) -> None:
        self._exit_requested = True
        if self._state_thread.is_alive():
            self._state_thread.join()

    def state(self) -> VehicleState:
        return self._state

    def _update_state(self) -> None:
        try:
            while self._exit_requested == False:
                state_change = self._state_queue.get()
                state_change_time = state_change.get('time')
                arbitration_id = state_change.get('arbitration_id')
                did_id = state_change.get('did_id')
                payload = state_change.get('payload')
                if did_id := state_change.get('did_id', None):
                    try:
                        if codec := self._codec_manager.codec(did_id):
                            decoded = codec.decode(None, bytearray(payload))
                            _LOGGER.debug(f"Event {state_change_time:.07f} {arbitration_id:04X}/{did_id:04X} payload={payload} {decoded.get('decoded')}")
                        else:
                            _LOGGER.error(f"No codec found for DID {arbitration_id:04X}/{did_id}")
                    except ValueError:
                        pass
                else:
                    _LOGGER.error(f"Missing DID")
                self._state_queue.task_done()
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
