import logging
import json

from typing import List, Any


_LOGGER = logging.getLogger('mme')


class ModuleManager:

    def __init__(self) -> None:
        self._modules = self._load_modules(file='json/modules.json')
        self._modules_by_name = self._modules_organized_by_name(self._modules)
        self._modules_by_id = self._modules_organized_by_id(self._modules)
        _LOGGER.debug("ModuleManager initialized")

    def modules(self) -> List[dict]:
        return self._modules

    def module(self, value: Any) -> dict:
        if type(value) is str:
            return self._modules_by_name.get(value, None)
        elif type(value) is int:
            return ModuleManager._modules_by_id.get(value, None)
        return None

    def arbitration_id(self, name: str) -> int:
        module_record = self._modules_by_name.get(name, None)
        return module_record.get('arbitration_id')

    def module_name(self, arbitration_id: int) -> str:
        module_record = self._modules_by_id.get(arbitration_id, None)
        return module_record.get('name')

    def _modules_organized_by_name(self, modules: List[dict]) -> dict:
        modules_by_names = {}
        for module in modules:
            modules_by_names[module.get('name')] = module
        return modules_by_names

    def _modules_organized_by_id(self, modules: List[dict]) -> dict:
        modules_by_id = {}
        for module in modules:
            modules_by_id[module.get('arbitration_id')] = module
        return modules_by_id

    def _load_modules(self, file: str) -> dict:
        with open(file) as infile:
            try:
                modules = json.load(infile)
            except FileNotFoundError as e:
                raise RuntimeError(f"{e}")
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON error in '{file}' at line {e.lineno}")
        return modules

    def _dump_modules(self, file: str, modules: dict) -> None:
        json_modules = json.dumps(modules, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_modules)
