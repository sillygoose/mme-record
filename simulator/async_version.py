#!/usr/bin/env python

"""
This example demonstrates how to use async IO with python-can.
"""

import asyncio
import struct
import can
from can.interfaces.socketcan import SocketcanBus


def print_message(msg):
    """Regular callback function. Can also be a coroutine."""
    print(msg)


async def main():
    bus = SocketcanBus(channel='can0') 
    reader = can.AsyncBufferedReader()
    logger = can.Logger("logfile.log")

    listeners = [
        print_message,      # Callback function
        reader,             # AsyncBufferedReader() listener
        logger,             # Regular Listener object
    ]
    # Create Notifier with an explicit loop to use for scheduling of callbacks
    loop = asyncio.get_event_loop()
    notifier = can.Notifier(bus, listeners, loop=loop)

    while True:
        try:
            msg = await reader.get_message()
            payload = msg.data
            tup = struct.unpack('>BBHL', payload)
            length, service, pid = tup[0], tup[1], tup[2]

            if length == 0x03 and service == 0x22:
                if pid == 0x417D:
                    response = can.Message(arbitration_id=0x7e8, is_extended_id=False, channel='can0', data=struct.pack('>BBHBBBB', 0x04, 0x62, pid, 0x02, 0x00, 0x00, 0x00))
                    bus.send(response)
                else:
                    response = can.Message(arbitration_id=0x7e8, is_extended_id=False, channel='can0', data=struct.pack('>BBBBBBBB', 0x03, 0x7F, 0x22, 0x31, 0x00, 0x00, 0x00, 0x00))
                    bus.send(response)

        except KeyboardInterrupt:
            break

    # Clean-up
    notifier.stop()
    bus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
