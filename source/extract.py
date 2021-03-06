"""
Simple utility to extract the DIDs asociated with a given module.
"""

import sys
import os
import logging

import logfiles
import version
from did_manager import DIDManager
from exceptions import FailedInitialization, RuntimeError


_LOGGER = logging.getLogger('mme')


class Extract:
    def __init__(self) -> None:
        self._did_manager = DIDManager()

    def start(self) -> None:
        dids = self._did_manager._load_dids(file='json/other/bcm_did_map_0000_FFFF.json')
        module_info = {
            'module': 'BCM',
            'arbitration_id': 1830,
            'arbitration_id_hex': '0726',
            'enable': True,
            'period': 10,
        }
        new_dids = []
        for did_record in dids:
            did_id = did_record.get('did_id')
            if self.filter(did_record):
                mi = module_info.copy()
                mi['dids'] = [{'did_name': '???', 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'codec_id': -1}]
                new_dids.append(mi)

        self._did_manager._save_dids('json/other/bcm_coverage.json', new_dids)
        _LOGGER.info(f"Extracted {len(new_dids)} DIDs to the output file")

    def stop(self) -> None:
        pass

    def filter(self, did) -> bool:
        length = did.get('length')
        modules = did.get('modules')
        if 1830 in modules: # and length <= 7:
            return True
        return False


def main() -> None:
    logfiles.start('log/extract.log')
    _LOGGER.info(f"Mustang Mach E DID Extractor Utility version {version.get_version()} PID is {os.getpid()}")
    try:
        extract = Extract()
        try:
            extract.start()
        except KeyboardInterrupt:
            print()
        finally:
            extract.stop()

    except KeyboardInterrupt:
        print()
    except RuntimeError as e:
        _LOGGER.error(f"Run time error: {e}")
    except FailedInitialization as e:
        _LOGGER.error(f"{e}")
    except Exception as e:
        _LOGGER.exception(f"Unexpected exception: {e}")


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
