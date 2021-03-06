import sys
import json
import logging

from can import Message
from can.interface import Bus

logger = logging.getLogger(__name__)


def message_length(data: bytearray) -> int:
    if data[0] & 0xf0:
        length = ((data[0] & 0xf) << 8) + data[1]
    else:
        length = data[0] & 0x7
    return length - 3


def test_one(can0: Bus, can1: Bus, did_id: int) -> dict:
    request_msg = Message(arbitration_id=0x726, data=[3, 0x22, did_id >> 8, did_id & 0xff, 0, 0, 0, 0], is_extended_id=False)
    max_length = -1
    timeout = 0.5
    responding_modules = []

    can0.send(request_msg)
    #can1.send(request_msg)

    while True:
        msg = can0.recv(timeout=timeout)
        if msg is None:
            break
        elif msg.is_error_frame:
            continue
        elif msg.data[0] == 0x03 and msg.data[1] == 0x7F:
            continue
        responding_modules.append(msg.arbitration_id - 8)
        length = message_length(msg.data)
        max_length = length if length > max_length else max_length
        logger.info(msg)

    """
    while True:
        msg = can1.recv(timeout=timeout)
        if msg is None:
            break
        elif msg.is_error_frame:
            continue
        elif msg.data[0] == 0x03 and msg.data[1] == 0x7F:
            continue
        responding_modules.append(msg.arbitration_id - 8)
        length = message_length(msg.data)
        max_length = length if length > max_length else max_length
        logger.info(msg)
    """

    responding_modules.sort()
    return {'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'length': max_length, 'modules': responding_modules}


def main() -> None:
    logging.getLogger().addHandler(logging.NullHandler())
    file_handler = logging.FileHandler(filename='did_map.log', mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S'))

    # Add some console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S'))

    # Create loggers
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("MME Data ID port scanner")
    try:
        can0 = Bus(bustype='socketcan', channel='can0', receive_own_messages=False)
        can1 = Bus(bustype='socketcan', channel='can1', receive_own_messages=False)
        filters = [{"can_id": 0x700, "can_mask": 0x600, "extended": False}]
        can0.set_filters(filters=filters)
        can1.set_filters(filters=filters)

        blocks = [
                    {'start': 0x0000, 'stop': 0x0FFF},
                    {'start': 0x1000, 'stop': 0x1FFF},
                    {'start': 0x2000, 'stop': 0x2FFF},
                    {'start': 0x3000, 'stop': 0x3FFF},
                    {'start': 0x4000, 'stop': 0x4FFF},
                    {'start': 0x5000, 'stop': 0x5FFF},
                    {'start': 0x6000, 'stop': 0x6FFF},
                    {'start': 0x7000, 'stop': 0x7FFF},
                    {'start': 0x8000, 'stop': 0x8FFF},
                    {'start': 0x9000, 'stop': 0x9FFF},
                    {'start': 0xA000, 'stop': 0xAFFF},
                    {'start': 0xB000, 'stop': 0xBFFF},
                    {'start': 0xC000, 'stop': 0xCFFF},
                    {'start': 0xD000, 'stop': 0xDFFF},
                    {'start': 0xE000, 'stop': 0xEFFF},
                    {'start': 0xF000, 'stop': 0xFFFF},
        ]

        big_did_map = []
        for block in blocks:
            did_map = []
            start = block.get('start')
            stop = block.get('stop')
            did = start

            logger.info(f"Starting scanning DIDs in range {start:04X}:{stop:04X}")
            while did <= stop :
                modules = test_one(can0=can0, can1=can1, did_id=did)
                if modules.get('length') >= 0:
                    did_map.append(modules)
                    big_did_map.append(modules)
                did += 1

            json_map = json.dumps(did_map, indent = 4, sort_keys=False)
            filename = f"did_map_{start:04X}_{stop:04X}.json"
            with open(filename, "w") as outfile:
                outfile.write(json_map)

        big_json_map = json.dumps(big_did_map, indent = 4, sort_keys=False)
        filename = f"bcm_did_map_0000_FFFF.json"
        with open(filename, "w") as outfile:
            outfile.write(big_json_map)

    except KeyboardInterrupt:
        pass
    finally:
        can0.shutdown()
        can1.shutdown()


if __name__ == '__main__':
    main()
