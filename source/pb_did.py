import struct
import logging

from typing import List

from codec_manager import CodecManager


_LOGGER = logging.getLogger('mme')


class PlaybackDID:

    def __init__(self, did_id: int, did_name: str, packing: str, bitfield: bool, modules: List[str], states: List[dict], codec_manager: CodecManager) -> None:
        self._did_id = did_id
        self._did_id_hex = f"{did_id:04X}"
        self._did_name = did_name
        self._packing = packing
        self._bitfield = bitfield
        self._modules = modules
        self._codec_manager = codec_manager
        self._states = []
        for state in states:
            # variable = state.get('name', None)
            value = state.get('value', None)
            self._states.append(value)

    def did_id(self) -> int:
        return self._did_id

    def did_name(self) -> str:
        return self._did_name

    def response(self) -> bytearray:
        response = bytearray()
        index = 0
        for state in self._states:
            if self._packing[index] == 'T':
                packing_format = '>L'
            elif self._packing[index] == 't':
                packing_format = '>l'
            else:
                packing_format = '>' + self._packing[index]
            postfix = struct.pack(packing_format, state)
            if self._packing[index] == 'T' or self._packing[index] == 't':
                # Pack as uint then remove high order byte to get A:B:C
                postfix = postfix[1:4]
            response = response + postfix
            index += 1
            if index == 1 and self._bitfield:
                break
        return response

    def new_event(self, event) -> None:
        payload = bytearray(event.get('payload'))
        unpacking_format = '>' + self._packing
        if self._packing.find('T') >= 0:
            unpacking_format = unpacking_format.replace('T', 'HB')
        unpacked_values = list(struct.unpack(unpacking_format, payload))
        if self._packing.find('T') >= 0:
            unpacked_values[0] = unpacked_values[0] * 256 + unpacked_values[1]

        index = 0
        for _ in self._states:
            self._states[index] = unpacked_values[index]
            self._log_event(event)
            index += 1
            if index == 1 and self._bitfield:
                break

    def _log_event(self, event: dict) -> None:
        event_time = event.get('time')
        arbitration_id = event.get('arbitration_id')
        did_id = event.get('did_id')
        payload = event.get('payload')
        if codec := self._codec_manager.codec(did_id):
            decoded = codec.decode(None, bytearray(payload))
            _LOGGER.debug(f"Event {event_time:.06f} {arbitration_id:04X}/{did_id:04X} payload={payload} {decoded.get('decoded')}")
        else:
            _LOGGER.debug(f"Event {event_time:.06f} {arbitration_id:04X}/{did_id:04X} payload={payload}")

    def did_id(self) -> int:
        return self._did_id

    def did_name(self) -> str:
        return self._did_name

    def did_packing(self) -> str:
        return self._packing

    def did_used_in(self) -> List[str]:
        return self._modules
