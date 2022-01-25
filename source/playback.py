import sys
import os
import logging
from typing import List

from module_manager import ModuleManager
from codec_manager import CodecManager
from did_manager import DIDManager

from pb_module import PlaybackModule
from pb_did import PlaybackDID
from pb_engine import PlaybackEngine

import version
import logfiles
from readconfig import parse_yaml_file, parse_command_line
from config.configuration import Configuration

from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Playback:
    def __init__(self, config: Configuration) -> None:
        self._config = config
        self._module_manager = ModuleManager()
        self._did_manager = DIDManager()
        self._codec_manager = CodecManager()
        self._dids = self._did_manager.dids()
        self._modules = self._add_modules(self._module_manager.modules())
        self._add_dids(self._dids)
        self._playback_engine = PlaybackEngine(config=config, active_modules=self._modules, module_manager=self._module_manager)

    def start(self) -> None:
        for module in self._modules.values():
            module.start()
        playback_thread = self._playback_engine.start()
        playback_thread.join()

    def stop(self) -> None:
        self._playback_engine.stop()
        for module in self._modules.values():
            module.stop()

    def _add_modules(self, module_list: List[dict]) -> None:
        active_modules = {}
        for module_record in module_list:
            module_name = module_record.get('name')
            channel = module_record.get('channel')
            arbitration_id = module_record.get('arbitration_id')
            if module_record.get('enable', False):
                if active_modules.get(module_name, None):
                    raise FailedInitialization(f"Module {module_name} is defined more than once")
                active_modules[module_name] = PlaybackModule(config=self._config, name=module_name, arbitration_id=arbitration_id, channel=channel, module_manager=self._module_manager)
        return active_modules

    def _add_dids(self, dids: List[dict]) -> None:
        self._dids_by_id = {}
        for did_item in dids:
            did = did_item.get('did_id')
            name = did_item.get('did_name')
            used_in_modules = did_item.get('modules')
            packing = did_item.get('packing')
            states = did_item.get('states')
            enable = did_item.get('enable')
            bitfield = did_item.get('bitfield', False)
            if enable:
                if self._dids_by_id.get(did, None) is not None:
                    raise FailedInitialization(f"DID {did:04X} is defined more than once")
                did_object = PlaybackDID(did_id=did, did_name=name, packing=packing, bitfield=bitfield, modules=used_in_modules, states=states, codec_manager=self._codec_manager)
                self._dids_by_id[did] = did_object

                for module in used_in_modules:
                    module_object = self._modules.get(module, None)
                    if module_object is not None:
                        module_object.add_did(did_object)


def main() -> None:
    try:
        yaml_file, log_file = parse_command_line(default_yaml='mme.yaml', default_log='playback.log')
        logfiles.start(log_file)
        _LOGGER.info(f"Mustang Mach E Playback Utility version {version.get_version()} PID is {os.getpid()}")

        if config := parse_yaml_file(yaml_file=yaml_file):
            try:
                playback = Playback(config=config.mme.playback)
                playback.start()
            except KeyboardInterrupt:
                print()
            except RuntimeError as e:
                _LOGGER.exception(f"Run time error: {e}")
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception: {e}")
            finally:
                playback.stop()

    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
