import sys
#import logging
from time import time, sleep
import json

from typing import List


#_LOGGER = logging.getLogger('mme')


def modules_organized_by_name(modules: List[dict]) -> dict:
    modules_by_names = {}
    for module in modules:
        modules_by_names[module.get('name')] = module
    return modules_by_names

def modules_organized_by_id(modules: List[dict]) -> dict:
    modules_by_id = {}
    for module in modules:
        modules_by_id[module.get('arbitration_id')] = module
    return modules_by_id

def load_modules(file: str) -> dict:
    with open(file) as infile:
        modules = json.load(infile)
    return modules

def get_module_name(arbitration_id: int) -> str:
    return modules_by_id.get(arbitration_id, '???')


modules = load_modules(file='mme_modules.json')
modules_by_name = modules_organized_by_name(modules)
modules_by_id = modules_organized_by_id(modules)


class Playback:

    def __init__(self, file: str=None) -> None:
        self._playback_file = file
        self._internal_clock = self._time_zero = int(time())

    def start(self) -> None:
        self._playback = self._load_playback(file=self._playback_file)
        self._currrent_playback = 0

    def run(self) -> None:
        while True:
            event = self._next_event()
            if event is None:
                return
            current_time = int(time()) - self._time_zero
            event_time = event.get('time')
            if current_time < event_time:
                sleep_for = event_time - current_time
                if sleep_for > 0:
                    if sleep_for > 5:
                        print(f"sleeping for {sleep_for} seconds")
                    sleep(sleep_for)
            current_time = int(time())
            print(f"{current_time-self._time_zero}: {self._decode_event(event)}")

    def stop(self) -> None:
        pass

    def _next_event(self) -> dict:
        if self._currrent_playback == len(self._playback):
            return None
        event = self._playback[self._currrent_playback]
        self._currrent_playback += 1
        return event

    def _decode_event(self, event: dict) -> str:
        module_name = get_module_name(event.get('id')).get('name')
        event['id'] = module_name
        event['payload'] = bytearray(event['payload'])
        return str(event)

    def _load_playback(self, file: str) -> dict:
        if file is None:
            return None
        with open(file) as infile:
            raw_playback = json.load(infile)
            playback = []
            for file_save in raw_playback:
                for record in file_save:
                    playback.append(record)
        return playback

    def _dump_playback(self, file: str, playback: dict) -> None:
        json_playback = json.dumps(playback, indent = 4, sort_keys=False)
        with open(file, "w") as outfile:
            outfile.write(json_playback)


def main() -> None:

    pb = Playback('data_log.json')
    pb.start()
    pb.run()
    pb.stop()

if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 10:
        main()
    else:
        print("python 3.10 or better required")
