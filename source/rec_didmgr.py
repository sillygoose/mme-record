import struct
import json
import logging

from typing import List

from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


class RecordDIDManager:

    _supported_dids = None
    _dids_by_name = None
    _dids_by_id = None

    def dids() -> List[dict]:
        return RecordDIDManager._supported_dids

    def did_name(did_id: int) -> str:
        did_record = RecordDIDManager._dids_by_id.get(did_id, None)
        return '???' if did_record is None else did_record.get('name')

    def __init__(self, config: dict) -> None:
        self._config = config
        RecordDIDManager._supported_dids = self._load_dids(file='json/mme_dids.json')
        RecordDIDManager._dids_by_name = self._dids_organized_by_name(RecordDIDManager._supported_dids)
        RecordDIDManager._dids_by_id = self._dids_organized_by_id(RecordDIDManager._supported_dids)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def _dids_organized_by_name(self, dids: List[dict]) -> dict:
        dids_by_names = {}
        for did in dids:
            dids_by_names[did.get('name')] = did
        return dids_by_names

    def _dids_organized_by_id(self, dids: List[dict]) -> dict:
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
            for did in RecordDIDManager._supported_dids:
                did_id = did.get('did', -1)
                name = did.get('name', '???')
                enable = did.get('enable', False)
                modules = did.get('modules', None)
                packing = did.get('packing', '???')
                states = did.get('states', None)
                did_str = f"did_id: {did_id:04X}, name: {name}, enable: {enable}, modules: {modules}, packing: {packing}, states: {states}"
                _LOGGER.info(did_str)
        else:
            json_str = json.dumps(RecordDIDManager._supported_dids, indent = 4, sort_keys=False)
            _LOGGER.info(json_str)
