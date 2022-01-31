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
        #self._codec_manager = CodecManager()

    def start(self) -> None:
        dids = self._did_manager._load_dids(file='json/other/did_coverage.json')
        new_dids = []
        for did_record in dids:
            did_id = did_record.get('did_id')
            length = did_record.get('length')
            modules = did_record.get('modules')
            if 'BCM' in modules and length <= 7:
                new_dids.append({'did_name': '???', 'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'codec_id': -1})

        extract_dids = {
            'module': 'BCM',
            'arbitration_id': 1830,
            'arbitration_id_hex': '0726',
            'enable': True,
            'period': 10,
            'dids': new_dids
        }
        self._did_manager._save_dids('json/did/bcm_coverage.json', extract_dids)

    def stop(self) -> None:
        pass


def main() -> None:
    logfiles.start('extract.log')
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
