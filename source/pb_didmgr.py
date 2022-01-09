import struct
import json
import logging

from typing import List

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


class PlaybackDIDManager:

    _supported_dids = None

    def dids() -> List[dict]:
        return PlaybackDIDManager._supported_dids

    def __init__(self, config: dict) -> None:
        self._config = config
        PlaybackDIDManager._supported_dids = self._load_dids(file='json/mme_dids.json')

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def _dids_organized_by_name(self, dids: List[dict]) -> dict:
        dids_by_names = {}
        for did in dids:
            dids_by_names[did.get('name')] = did
        return dids_by_names

    def _dids_organized_by_did(self, dids: List[dict]) -> dict:
        dids_by_id = {}
        for did in dids:
            dids_by_id[did.get('did')] = did
        return dids_by_id

    def _load_dids(self, file: str) -> dict:
        with open(file) as infile:
            try:
                dids = json.load(infile)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        return dids

    def _dump_dids(self, file: str, dids: dict) -> None:
        json_dids = json.dumps(dids, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_dids)

    def show_dids(self, show_json: bool = False) -> None:
        if show_json == False:
            for did in PlaybackDIDManager._supported_dids:
                did_id = did.get('did', -1)
                name = did.get('name', '???')
                enable = did.get('enable', '???')
                modules = did.get('modules', '???')
                packing = did.get('packing', '???')
                states = did.get('states', '???')
                did_str = f"did: {did_id:04X}, name: {name}, enable: {enable}, modules: {modules}, packing: {packing}, states: {states}"
                _LOGGER.info(did_str)
        else:
            json_str = json.dumps(PlaybackDIDManager._supported_dids, indent = 4, sort_keys=False)
            _LOGGER.info(json_str)


class PlaybackDID:

    def __init__(self, did: int, name: str, packing: str, modules: List[str], states: List[dict]) -> None:
        self._did = did
        self._name = name
        self._packing = packing
        self._modules = modules
        self._states = []
        for state in states:
            # variable = state.get('name', None)
            value = state.get('value', None)
            self._states.append(value)

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
            index += 1

    def did(self) -> int:
        return self._did

    def name(self) -> str:
        return self._name

    def packing(self) -> str:
        return self._packing

    def used_in(self) -> List[str]:
        return self._modules
