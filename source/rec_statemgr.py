import logging
from time import sleep, time

from threading import Thread
from queue import Empty, Full, Queue
from typing import List

from rec_filemgr import RecordFileManager
import rec_codecs


_LOGGER = logging.getLogger('mme')


class RecordStateManager:

    gwm = [
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x411F, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6035, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6037, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6038, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xC014, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xC015, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD021, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD023, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD07A, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD07B, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD100, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD111, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0A, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0B, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0C, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0D, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE2C, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xEEE1, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xF163, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD21, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD29, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6036, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6039, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE2D, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE2E, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE31, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xEEE0, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD19, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x0479, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x602F, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x603A, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
            #    {'did': 0xC011, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE11, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE18, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE1B, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD04F, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0E, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xF166, 'codec': rec_codecs.CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD20, 'codec': rec_codecs.CodecNull},
            ]},
    ]

    mach_e = [
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x411F, 'codec': rec_codecs.CodecKeyState},            # Ignition state
            ]},
        {'module': 'IPC', 'address': 0x720, 'bus': 'can1', 'dids': [
                {'did': 0x404C, 'codec': rec_codecs.CodecOdometer},            # Odometer
                {'did': 0x6310, 'codec': rec_codecs.CodecGearDisplayed},       # Gear displayed
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

    def __init__(self, config: dict, request_queue: Queue, response_queue: Queue) -> None:
        self._config = config
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._exit_requested = False
        self._sync_queue = Queue(maxsize=2)
        self._request_thread = Thread(target=self._request_task, args=(self._sync_queue,), name='state_request')
        self._response_thread = Thread(target=self._response_task, args=(self._sync_queue,), name='state_response')
        self._file_manager = RecordFileManager(config)
        self._start_time = int(time())
        self._did_state_cache = {}

    def start(self) -> List[Thread]:
        fm_thread = self._file_manager.start()
        self._exit_requested = False
        self._request_thread.start()
        self._response_thread.start()
        return [self._request_thread, self._response_thread,fm_thread[0]]

    def stop(self) -> None:
        self._file_manager.stop()
        self._exit_requested = True
        if self._request_thread.is_alive():
            self._request_thread.join()
        if self._response_thread.is_alive():
            self._response_thread.join()

    def _request_task(self, sync_queue: Queue) -> None:
        try:
            while self._exit_requested == False:
                try:
                    self._request_queue.put(RecordStateManager.mach_e, block=True)
                    sync_queue.get()
                except Full:
                    _LOGGER.error(f"no space in the request queue")
                    self._exit_requested = True
        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return

    def _response_task(self, sync_queue: Queue) -> None:
        try:
            while self._exit_requested == False:
                try:
                    response_batch = self._response_queue.get(block=True, timeout=0.5)
                    sync_queue.put(1)
                except Empty:
                    if self._exit_requested == False:
                        continue
                    return

                for response_record in response_batch:
                    arbitration_id = response_record.get('arbitration_id')
                    response = response_record.get('response')
                    current_time = round(time() - self._start_time, ndigits=1)
                    for did in response.service_data.values:
                        key = f"{arbitration_id:04X} {did:04X}"
                        payload = response.service_data.values[did].get('payload')
                        if self._did_state_cache.get(key, None) is None:
                            self._did_state_cache[key] = {'time': current_time, 'payload': payload}
                            self._file_manager.put({'time': current_time, 'arbitration_id': arbitration_id, 'did': did, 'payload': list(payload)})
                            _LOGGER.info(f"{arbitration_id:04X}/{did:04X}: {response.service_data.values[did].get('decoded')}")
                        else:
                            if self._did_state_cache.get(key).get('payload') != payload:
                                self._did_state_cache[key] = {'time': current_time, 'payload': payload}
                                self._file_manager.put({'time': current_time, 'arbitration_id': arbitration_id, 'did': did, 'payload': list(payload)})
                                _LOGGER.info(f"{arbitration_id:04X}/{did:04X}: {response.service_data.values[did].get('decoded')}")

        except RuntimeError as e:
            _LOGGER.error(f"Run time error: {e}")
            return
