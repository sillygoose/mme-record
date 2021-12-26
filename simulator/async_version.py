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
    logger = can.Logger("logfile.csv")

    listeners = [
        print_message,      # Callback function
        reader,             # AsyncBufferedReader() listener
        logger,             # Regular Listener object
    ]
    notifier = can.Notifier(bus, listeners, loop=asyncio.get_event_loop())

    while True:
        try:
            msg = await reader.get_message()
            payload = msg.data
            length, service, pid = struct.unpack_from('>BBH', payload, 0)

            if length == 0x00:
                break
            
            if length == 0x03 and service == 0x22:
                buffer = bytearray(8)
                if pid == 0x4028:
                    struct.pack_into('>BBHB', buffer, 0, 0x04, 0x62, pid, 0x5B)
                elif pid == 0x404C:
                    struct.pack_into('>BBHHB', buffer, 0, 0x06, 0x62, pid, 0x00DC, 0x66)
                elif pid == 0x417D:
                    struct.pack_into('>BBHB', buffer, 0, 0x04, 0x62, pid, 0x02)
                else:
                    struct.pack_into('>BBBB', buffer, 0, 0x03, 0x7F, 0x22, 0x31)
                response = can.Message(arbitration_id=0x7e8, is_extended_id=False, channel='can0', data=buffer)
                bus.send(response)

        except KeyboardInterrupt:
            break

    # Clean-up
    notifier.stop()
    bus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
