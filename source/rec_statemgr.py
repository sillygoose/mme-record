import logging
from time import sleep, time

from threading import Thread
from queue import Empty, Full, Queue
from typing import List
import json

from rec_filemgr import RecordFileManager
from rec_didmgr import RecordDIDManager

from codecmgr import *
from codec import CodecId


_LOGGER = logging.getLogger('mme')


class RecordStateManager:

    gwm = [
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x411F, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6035, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6037, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6038, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xC014, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xC015, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD021, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD023, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD07A, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD07B, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD100, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD111, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0A, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0B, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0C, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0D, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE2C, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xEEE1, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xF163, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD21, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD29, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6036, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x6039, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE2D, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE2E, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE31, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xEEE0, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD19, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x0479, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x602F, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x603A, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
            #    {'did': 0xC011, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE11, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE18, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE1B, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xD04F, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xDE0E, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xF166, 'codec': CodecNull},
            ]},
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0xFD20, 'codec': CodecNull},
            ]},
    ]

    mach_e = [
        {'module': 'GWM', 'address': 0x716, 'bus': 'can0', 'dids': [
                {'did': 0x411F, 'codec': CodecKeyState},            # Ignition state
            ]},
        {'module': 'IPC', 'address': 0x720, 'bus': 'can1', 'dids': [
                {'did': 0x404C, 'codec': CodecOdometer},            # Odometer
                {'did': 0x6310, 'codec': CodecGearDisplayed},       # Gear displayed
            ]},
        {'module': 'SOBDM', 'address': 0x7E2, 'bus': 'can0', 'dids': [
                {'did': 0xDD00, 'codec': CodecTime},                # Time
                {'did': 0xDD04, 'codec': CodecInteriorTemp},        # Interior temp
                {'did': 0xDD05, 'codec': CodecExteriorTemp},        # External temp
                {'did': 0x1E12, 'codec': CodecGearCommanded},       # Gear commanded
                {'did': 0x48B7, 'codec': CodecEvseDigitalMode},     # EVSE digital mode
            ]},
        {'module': 'APIM', 'address': 0x7D0, 'bus': 'can1', 'dids': [
                {'did': 0x8012, 'codec': CodecGPS},                 # GPS data
            ]},
        {'module': 'PCM', 'address': 0x7E0, 'bus': 'can0', 'dids': [
                {'did': 0x1505, 'codec': CodecHiresSpeed},          # Speed
            ]},
        {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
                {'did': 0x4801, 'codec': CodecHvbSoc},              # HVB SOC
                {'did': 0x4845, 'codec': CodecHvbSocD},             # HVB SOC displayed
                {'did': 0x4848, 'codec': CodecHvbEte},              # HVB Energy to empty
            ]},
        {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
                {'did': 0x4800, 'codec': CodecHvbTemp},             # HVB temp
                {'did': 0x480D, 'codec': CodecHvbVoltage},          # HVB Voltage
                {'did': 0x48F9, 'codec': CodecHvbCurrent},          # HVB Current
            ]},
        {'module': 'BECM', 'address': 0x7E4, 'bus': 'can0', 'dids': [
                {'did': 0x484F, 'codec': CodecChargerStatus},       # Charger status
                {'did': 0x4851, 'codec': CodecEvseType},            # EVSE type
            ]},
        {'module': 'BCM', 'address': 0x726, 'bus': 'can0', 'dids': [
                {'did': 0x4028, 'codec': CodecLvbSoc},              # LVB State of Charge
                {'did': 0x402A, 'codec': CodecLvbVoltage},          # LVB Voltage
                {'did': 0x402B, 'codec': CodecLvbCurrent},          # LVB Current
            ]},
    ]

    def _write_state_dids(self, state_dids: List, file: str) -> None:
        output_modules = []
        for module in state_dids:
            module_name = module.get('module')
            arbitration_id = module.get('address')
            output_dids = []
            dids = module.get('dids')
            for did in dids:
                did_id = did.get('did')
                name = RecordDIDManager.did_name(did_id)
                codec_id = did_id
                output_dids.append({'did_name': name, 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'codec_id': codec_id})
            new_module = {'module': module_name, 'arbitration_id': arbitration_id, 'arbitration_id_hex': f"{arbitration_id:04X}", 'dids': output_dids}
            output_modules.append(new_module)
        json_dids = json.dumps(output_modules, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_dids)

    def _load_state_definition(self, file: str) -> List[dict]:
        with open(file) as infile:
            try:
                state_definition = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")

        for module in state_definition:
            dids = module.get('dids')
            for did in dids:
                codec_id = did.get('codec_id')
                codec = self._codec_manager.codec(codec_id)
                did['codec'] = codec
        return state_definition

    def __init__(self, config: dict, request_queue: Queue, response_queue: Queue) -> None:
        #self._write_state_dids(state_dids=RecordStateManager.mach_e, file='log/test.json')
        self._config = config
        self._codec_manager = CodecManager(config=self._config)
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._exit_requested = False
        self._sync_queue = Queue(maxsize=2)
        self._request_thread = Thread(target=self._request_task, args=(self._sync_queue,), name='state_request')
        self._response_thread = Thread(target=self._response_task, args=(self._sync_queue,), name='state_response')
        self._file_manager = RecordFileManager(config)
        self._start_time = int(time())
        self._did_state_cache = {}
        self._state = None

    def start(self) -> List[Thread]:
        self._exit_requested = False
        self._current_state_definition = self._load_state_definition('log/test.json')
        self._codec_manager.start()
        fm_thread = self._file_manager.start()
        self._request_thread.start()
        self._response_thread.start()
        return [self._request_thread, self._response_thread, fm_thread[0]]

    def stop(self) -> None:
        self._codec_manager.stop()
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
                    self._request_queue.put(self._current_state_definition, block=True)
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
