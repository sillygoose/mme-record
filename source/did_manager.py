import logging
import json

from typing import List, Tuple

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


class DIDManager:

    def __init__(self) -> None:
        self._dids = self._load_dids(file='json/did/dids.json')
        self._dids_by_name = self._dids_organized_by_name(self._dids)
        self._dids_by_id = self._dids_organized_by_id(self._dids)

    def dids(self) -> List[dict]:
        return self._dids

    def did_name(self, did_id: int) -> str:
        did_record = self._dids_by_id.get(did_id, None)
        return None if did_record is None else did_record.get('did_name')

    def did_packing(self, did_id: int) -> Tuple[str, int]:
        _packing_lengths = {'B': 1, 'b': 1, 'H': 2, 'h': 2, 't': 3, 'T': 3, 'L': 4, 'l': 4}
        did_record = self._dids_by_id.get(did_id, None)
        packing = did_record.get('packing', None)
        packing_length = _packing_lengths.get(packing, 0)
        return (packing, packing_length)

    def did_states(self, did_id: int) -> List[dict]:
        did_record = self._dids_by_id.get(did_id, None)
        return None if did_record is None else did_record.get('states')

    def _dids_organized_by_name(self, dids: List[dict]) -> dict:
        dids_by_names = {}
        for did in dids:
            dids_by_names[did.get('did_name')] = did
        return dids_by_names

    def _dids_organized_by_id(self, dids: List[dict]) -> dict:
        dids_by_id = {}
        for did in dids:
            dids_by_id[did.get('did_id')] = did
        return dids_by_id

    def _load_dids(self, file: str) -> dict:
        with open(file) as infile:
            try:
                dids = json.load(infile)
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        return dids

    def _save_dids(self, file: str, dids: dict) -> None:
        json_dids = json.dumps(dids, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_dids)
        _LOGGER.info(f"Wrote DID file '{file}'")

    def show_dids(self, show_json: bool = False) -> None:
        if show_json == False:
            for did in self._dids:
                did_id = did.get('did_id', -1)
                did_name = did.get('did_name', '???')
                enable = did.get('enable', False)
                modules = did.get('modules', [])
                packing = did.get('packing', '?')
                states = did.get('states', [])
                did_str = f"did_id: {did_id:04X}, did_name: {did_name}, enable: {enable}, modules: {modules}, packing: {packing}, states: {states}"
                _LOGGER.info(did_str)
        else:
            json_str = json.dumps(self._supported_dids, indent = 4, sort_keys=False)
            _LOGGER.info(json_str)
