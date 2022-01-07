import sys
from queue import Queue
import logging
from typing import List

import module
from module import Module

import did
from did import DID
from pbengine import PlaybackEngine

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Playback:
    def __init__(self, config: dict, modules: List[dict], dids: List[dict]) -> None:
        self._config = dict(config.mme.playback)
        self._modules = None
        self._module_event_queues = None
        self._add_modules(modules)
        self._add_dids(dids)
        self._playback_engine = PlaybackEngine(config=self._config, queues=self._module_event_queues)

    def start(self) -> None:
        for module in self._modules.values():
            module.start()
        self._playback_engine.start()

    def stop(self) -> None:
        for module in self._modules.values():
            module.stop()

    def event_queues(self) -> dict:
        return self._module_event_queues

    def _add_modules(self, modules: List[dict]) -> None:
        self._modules = {}
        self._module_event_queues = {}
        for module_record in modules:
            name = module_record.get('name')
            channel = module_record.get('channel')
            arbitration_id = module_record.get('arbitration_id')
            enable = module_record.get('enable')
            if enable:
                if self._modules.get(module, None) is not None:
                    raise FailedInitialization(f"Module {module} is defined more than once")
                event_queue = Queue(maxsize=12)
                self._module_event_queues[name] = event_queue
                self._modules[name] = Module(name=name, event_queue=event_queue, channel=channel, arbitration_id=arbitration_id)
                _LOGGER.debug(f"Added module '{module}' to playback")

    def _add_dids(self, dids: List[dict]) -> None:
        self._dids_by_id = {}
        for did_item in dids:
            did = did_item.get('did')
            name = did_item.get('name')
            used_in_modules = did_item.get('modules')
            packing = did_item.get('packing')
            states = did_item.get('states')
            enable = did_item.get('enable')
            if enable:
                if self._dids_by_id.get(did, None) is not None:
                    raise FailedInitialization(f"DID {did:04X} is defined more than once")
                did_object = DID(did=did, name=name, packing=packing, modules=used_in_modules, states=states)
                self._dids_by_id[did] = did_object

                for module in used_in_modules:
                    module_object = self._modules.get(module, None)
                    if module_object is not None:
                        module_object.add_did(did_object)

                _LOGGER.debug(f"Added DID {did:04X}")


def main() -> None:

    logfiles.start()
    _LOGGER.info(f"Mustang Mach E Playback Utility version {version.get_version()}")

    try:
        config = read_config(yaml_file='mme.yaml')
        if config is None:
            return
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception: {e}")
        return

    try:
        mme = Playback(config=config, modules=module.modules(), dids=did.dids())
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected exception setting up Playback: {e}")
        return

    try:
        mme.start()
    except KeyboardInterrupt:
        pass
    except RuntimeError:
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
