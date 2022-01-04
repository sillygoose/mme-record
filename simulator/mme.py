import sys
import os
import time
from queue import Queue
import logging
from typing import List

from module import Module, builtin_modules
from did import DID, builtin_dids
from playback import Playback

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization


_LOGGER = logging.getLogger('mme')


class MustangMachE:
    def __init__(self, config: dict) -> None:
        self._modules = {}
        self._config = config.mme
        self._modules = {}
        self._module_event_queues = {}
        self._dids_by_id = {}

    def start(self) -> None:
        for module in self._modules.values():
            module.start()

    def stop(self) -> None:
        for module in self._modules.values():
            module.stop()

    def event_queues(self) -> dict:
        return self._module_event_queues

    def add_custom_modules(self, modules: dict) -> None:
        if len(modules) == 0:
            raise FailedInitialization("Must define at least one module in YAML file")

        for module in modules:
            module_settings = module.get('module', None)
            if module_settings is None:
                raise FailedInitialization("Error parsing custom module definition in YAML file")
            name = module_settings.get('name', None)
            channel = module_settings.get('channel', None)
            arbitration_id = module_settings.get('arbitration_id', None)
            self._modules[name] = Module(name=name, channel=channel,arbitration_id=arbitration_id)

    def add_custom_dids(self, dids: dict) -> None:
        if len(dids) == 0:
            raise FailedInitialization("Must define at least one DID in YAML file")

        for did_item in dids:
            did = did_item.get('did', None)
            if did is None:
                raise FailedInitialization("Error parsing custom DID definition in YAML file")

            id = did.get('id', None)
            name = did.get('name', None)
            packing = did.get('packing', None)
            modules = did.get('modules', None)
            states = did.get('states', None)

            if self._dids_by_id.get(id, None) is not None:
                raise FailedInitialization(f"DID {did:04X} is defined more than once in the YAML file")
            did_object = DID(id=id, name=name, packing=packing, modules=modules, states=states)
            self._dids_by_id[id] = did_object
            _LOGGER.debug(f"Added DID {id:04X} to simulator")

            did_modules = did_object.used_in()
            for module_name in did_modules:
                module_object = self._modules.get(module_name, None)
                if module_object is not None:
                    module_object.add_did(did_object)

    def add_builtin_modules(self, modules: List[dict]) -> None:
        for module in modules:
            name = module.get('name')
            channel = module.get('channel')
            arbitration_id = module.get('arbitration_id')
            enable = module.get('enable')
            if enable:
                #if self._modules.get(module, None) is not None:
                #    raise FailedInitialization(f"Module {module} is defined more than once")
                event_queue = Queue(maxsize=10)
                self._module_event_queues[name] = event_queue
                self._modules[name] = Module(name=name, event_queue=event_queue, channel=channel, arbitration_id=arbitration_id)
                _LOGGER.debug(f"Added builtin module '{module}' to simulator")

    def add_builtin_dids(self, dids: List[int]) -> None:
        for did in dids:
            if self._dids_by_id.get(did, None) is not None:
                raise FailedInitialization(f"DID {did:04X} is defined more than once")
            did_object = DID(id=did)
            self._dids_by_id[did] = did_object
            _LOGGER.debug(f"Added builtin DID {did:04X} to simulator")

            did_modules = did_object.used_in()
            for module_name in did_modules:
                module_object = self._modules.get(module_name, None)
                if module_object is not None:
                    module_object.add_did(did_object)


def main() -> None:

    logfiles.start()
    _LOGGER.info(f"Mustang Mach E Simulator version {version.get_version()}, PID is {os.getpid()}")

    try:
        config = read_config()
        if config is None:
            return
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        mme = MustangMachE(config=config)
        builtin = config.mme.builtin
        if builtin.modules == True:
            list_of_modules = builtin_modules()
            mme.add_builtin_modules(modules=list_of_modules)
        if 'custom' in config.mme.keys():
            custom = config.mme.custom
            if 'modules' in custom.keys():
                mme.add_custom_modules(custom.modules)

        if builtin.dids == True:
            mme.add_builtin_dids(builtin_dids())
        if 'custom' in config.mme.keys():
            custom = config.mme.custom
            if 'dids' in custom.keys():
                mme.add_custom_dids(custom.dids)
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        pb = Playback(file='playback.json', queues=mme.event_queues(), start_at=0)
        mme.start()
        pb.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
    finally:
        mme.stop()


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
