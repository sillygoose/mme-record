import sys
from queue import Queue
import logging
from typing import List

from pb_modmgr import PlaybackModuleManager, PlaybackModule
from pb_didmgr import PlaybackDIDManager, PlaybackDID
from pb_statemgr import PlaybackStateManager
from pb_engine import PlaybackEngine

import version
import logfiles
from readconfig import read_config

from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Playback:
    def __init__(self, config: dict) -> None:
        self._config = config
        self._state_update_queue = Queue(maxsize=20)
        self._module_event_queues = None
        self._state_manager = PlaybackStateManager(config=self._config, state_queue=self._state_update_queue)
        self._module_manager = PlaybackModuleManager(config=self._config)
        self._modules = PlaybackModuleManager.modules()
        self._did_manager = PlaybackDIDManager(config=self._config)
        self._dids = PlaybackDIDManager.dids()
        self._add_modules(self._modules)
        self._add_dids(self._dids)
        self._playback_engine = PlaybackEngine(config=self._config, module_event_queues=self._module_event_queues)

    def start(self) -> None:
        self._module_manager.start()
        self._did_manager.start()
        threads = []
        threads.append(self._state_manager.start())
        for module in self._modules.values():
            threads.append(module.start())
        threads.append(self._playback_engine.start())
        for thread_list in threads:
            for thread in thread_list:
                thread.join()

    def stop(self) -> None:
        for module in self._modules.values():
            module.stop()
        self._did_manager.stop()
        self._module_manager.stop()
        self._state_manager.stop()

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
                if self._modules.get(name, None) is not None:
                    raise FailedInitialization(f"Module {name} is defined more than once")
                event_queue = Queue(maxsize=12)
                self._module_event_queues[name] = event_queue
                self._modules[name] = PlaybackModule(name=name, arbitration_id=arbitration_id, channel=channel, event_queue=event_queue, state_queue=self._state_update_queue)
                _LOGGER.debug(f"Added module '{name}' to playback")

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
                did_object = PlaybackDID(did=did, name=name, packing=packing, modules=used_in_modules, states=states)
                self._dids_by_id[did] = did_object

                for module in used_in_modules:
                    module_object = self._modules.get(module, None)
                    if module_object is not None:
                        module_object.add_did(did_object)

                _LOGGER.debug(f"Added DID {did:04X}")


def main() -> None:

    logfiles.start('log/playback.log')
    _LOGGER.info(f"Mustang Mach E Playback Utility version {version.get_version()}")

    try:
        config = read_config(yaml_file='mme.yaml')
        if config is None:
            return
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")
        return

    try:
        playback_config = dict(config.mme.playback)
        playback = Playback(config=playback_config)
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
        return
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception setting up Playback: {e}")
        return

    try:
        playback.start()
    except KeyboardInterrupt:
        print()
    except RuntimeError as e:
        _LOGGER.exception(f"Run time error: {e}")
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")
    finally:
        playback.stop()


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
