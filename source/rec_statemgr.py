import logging
from time import sleep, time

from threading import Thread
from queue import Empty, Full, Queue
from typing import List

from rec_filemgr import RecordFileManager
import rec_codecs

#from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class RecordStateManager:
    mach_e = [
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x411F, 'codec': rec_codecs.CodecKeyState},            # Ignition state
            ]},
        {'module': 'SOBDM', 'address': 0x7E2, 'bus': 'can0', 'dids': [
                {'did': 0xDD00, 'codec': rec_codecs.CodecTime},                # Time
                #{'did': 0xDD04, 'codec': rec_codecs.CodecInteriorTemp},        # Interior temp
                {'did': 0xDD05, 'codec': rec_codecs.CodecExteriorTemp},        # External temp
                {'did': 0x1E12, 'codec': rec_codecs.CodecGearCommanded},       # Gear commanded
                #{'did': 0x48B7, 'codec': rec_codecs.CodecEVSEDigitalMode},     # EVSE digital mode
            ]},
        {'module': 'APIM', 'address': 0x7D0, 'bus': 'can1', 'dids': [
                {'did': 0x8012, 'codec': rec_codecs.CodecGPS},                 # GPS data
            ]},
        {'module': 'IPC', 'address': 0x720, 'bus': 'can1', 'dids': [
                {'did': 0x404C, 'codec': rec_codecs.CodecOdometer},            # Odometer
                {'did': 0x6310, 'codec': rec_codecs.CodecGearDisplayed},       # Gear displayed
            ]},
        {'module': 'PCM', 'address': 0x7E0, 'bus': 'can0', 'dids': [
                {'did': 0x1505, 'codec': rec_codecs.CodecHiresSpeed},          # Speed
            ]},
        {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
                {'did': 0x4801, 'codec': rec_codecs.CodecHvbSoc},              # HVB SOC
                {'did': 0x4845, 'codec': rec_codecs.CodecHvbSocD},             # HVB SOC displayed
                {'did': 0x4848, 'codec': rec_codecs.CodecHvbEte},              # HVB Energy to empty
            ]},
        {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
                {'did': 0x4800, 'codec': rec_codecs.CodecHvbTemp},             # HVB temp
                {'did': 0x480D, 'codec': rec_codecs.CodecHvbVoltage},          # HVB Voltage
                {'did': 0x48F9, 'codec': rec_codecs.CodecHvbCurrent},          # HVB Current
            ]},
        {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
                {'did': 0x484F, 'codec': rec_codecs.CodecChargerStatus},       # Charger status
                {'did': 0x4851, 'codec': rec_codecs.CodecEvseType},            # EVSE type
            ]},
        {'module': 'BCM', 'address': 0x726, 'bus': 'can0', 'dids': [
                {'did': 0x4028, 'codec': rec_codecs.CodecLvbSoc},              # LVB State of Charge
                {'did': 0x402A, 'codec': rec_codecs.CodecLvbVoltage},          # LVB Voltage
                {'did': 0x402B, 'codec': rec_codecs.CodecLvbCurrent},          # LVB Current
            ]},
    ]

    did_state_cache = {}

    def __init__(self, config: dict, request_queue: Queue, response_queue: Queue) -> None:
        self._config = config
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._exit_requested = False
        self._request_thread = Thread(target=self._request_task, name='state_request')
        self._response_thread = Thread(target=self._response_task, name='state_response')
        self._file_manager = RecordFileManager(config)
        self._start_time = int(time())

    def start(self) -> List[Thread]:
        self._file_manager.start()
        self._exit_requested = False
        self._request_thread.start()
        self._response_thread.start()
        return [self._request_thread, self._response_thread]

    def stop(self) -> None:
        self._file_manager.stop()
        self._exit_requested = True
        if self._request_thread.is_alive():
            self._request_thread.join()
        if self._response_thread.is_alive():
            self._response_thread.join()

    def _request_task(self) -> None:
        try:
            while self._exit_requested == False:
                try:
                    self._request_queue.put(RecordStateManager.mach_e, block=True)
                    sleep(0.5)
                except Full:
                    _LOGGER.error(f"no space in the request queue")
                    self._exit_requested = True
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def _response_task(self) -> None:
        try:
            while self._exit_requested == False:
                try:
                    response_record = self._response_queue.get(block=True, timeout=None)
                    arbitration_id = response_record.get('arbitration_id')
                    response = response_record.get('response')
                    current_time = round(time() - self._start_time, ndigits=1)
                    for did in response.service_data.values:
                        key = f"{arbitration_id:04X} {did:04X}"
                        payload = response.service_data.values[did].get('payload')
                        if RecordStateManager.did_state_cache.get(key, None) is None:
                            RecordStateManager.did_state_cache[key] = payload
                            self._file_manager.put({'time': current_time, 'arbitration_id': arbitration_id, 'did': did, 'payload': list(payload)})
                            _LOGGER.info(f"{response.service_data.values[did].get('decoded')}")
                        else:
                            if RecordStateManager.did_state_cache.get(key) != payload:
                                RecordStateManager.did_state_cache[key] = payload
                                self._file_manager.put({'time': current_time, 'arbitration_id': arbitration_id, 'did': did, 'payload': list(payload)})
                                _LOGGER.info(f"{response.service_data.values[did].get('decoded')}")
                except Empty:
                    _LOGGER.error(f"timed out waiting on a response")
                    continue
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
