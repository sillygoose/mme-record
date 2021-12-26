#!/usr/bin/env python

"""
This example demonstrates how to use async IO with python-can.
"""

import asyncio
import can
from can.interfaces.socketcan import SocketcanBus


def print_message(msg):
    """Regular callback function. Can also be a coroutine."""
    print(msg)


async def main():
    bus = SocketcanBus(channel='can0') 
    #bus = can.Bus("can0", bustype="SocketCANBus", receive_own_messages=False)

    reader = can.AsyncBufferedReader()
    logger = can.Logger("logfile.log")

    listeners = [
        print_message,  # Callback function
        reader,  # AsyncBufferedReader() listener
        logger,  # Regular Listener object
    ]
    # Create Notifier with an explicit loop to use for scheduling of callbacks
    loop = asyncio.get_event_loop()
    notifier = can.Notifier(bus, listeners, loop=loop)
    # Start sending first message
    # bus.send(can.Message(arbitration_id=0x7e8))

    print("Bouncing 10 messages...")
    for _ in range(10):
        # Wait for next message from AsyncBufferedReader
        msg = await reader.get_message()
        # Delay response
        await asyncio.sleep(0.5)
        # msg.arbitration_id += 1
        bus.send(msg)
    # Wait for last message to arrive
    await reader.get_message()
    print("Done!")

    # Clean-up
    notifier.stop()
    bus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
