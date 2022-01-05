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
        for did_item in dids:
            did = did_item.get('did')
            name = did_item.get('name')
            modules = did_item.get('modules')
            packing = did_item.get('packing')
            states = did_item.get('states')
            enable = did_item.get('enable')
            if enable:
                if self._dids_by_id.get(did, None) is not None:
                    raise FailedInitialization(f"DID {did:04X} is defined more than once")
                did_object = DID(did=did, name=name, packing=packing, modules=modules, states=states)
                self._dids_by_id[did] = did_object

                for module in modules:
                    module_object = self._modules.get(module, None)
                    if module_object is not None:
                        module_object.add_did(did_object)

                _LOGGER.debug(f"Added DID {did:04X} to simulator")


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

        list_of_modules = builtin_modules()
        mme.add_builtin_modules(modules=list_of_modules)
        list_of_dids = builtin_dids()
        mme.add_builtin_dids(list_of_dids)

    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        pb = Playback(file='json/playback.json', queues=mme.event_queues(), start_at=0)
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
