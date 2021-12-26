import time
import isotp
import logging
import threading
import struct

from can.interfaces.socketcan import SocketcanBus


_TIMEOUT = 5.0
isotp_params = {
   'stmin' : 32,                                            # Will request the sender to wait 32ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9
   'blocksize' : 8,                                         # Request the sender to send 8 consecutives frames before sending a new flow control message
   'wftmax' : 0,                                            # Number of wait frame allowed before triggering an error
   'tx_data_length' : 8,                                    # Link layer (CAN layer) works with 8 byte payload (CAN 2.0)
   'tx_data_min_length' : 8,                                # Minimum length of CAN messages. When different from None, messages are padded to meet this length. Works with CAN 2.0 and CAN FD.
   'tx_padding' : 0x00,                                     # Will pad all transmitted CAN messages with byte 0x00.
   'rx_flowcontrol_timeout' : int(_TIMEOUT * 1000),         # Triggers a timeout if a flow control is awaited for more than 1000 milliseconds
   'rx_consecutive_frame_timeout' : int(_TIMEOUT * 1000),   # Triggers a timeout if a consecutive frame is awaited for more than 1000 milliseconds
   'squash_stmin_requirement' : False,                      # When sending, respect the stmin requirement of the receiver. If set to True, go as fast as possible.
   'max_frame_size' : 4095                                  # Limit the size of receive frame.
}


class CanModule:
    def __init__(self):
        self.exit_requested = False

    def start(self):
        self.exit_requested = False
        self.thread = threading.Thread(target=self.thread_task)
        self.thread.start()

    def stop(self):
        self.exit_requested = True
        if self.thread.is_alive():
            self.thread.join()

    def error_handler(self, error):
        logging.warning('IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def thread_task(self):
        while self.exit_requested == False:
            self.stack.process()                # Non-blocking
            time.sleep(self.stack.sleep_time()) # Variable sleep time based on state machine state

    def shutdown(self):
        self.stop()


class IPC(CanModule):
    def __init__(self, name, channel, id):
        self.name = name
        self.channel = channel
        self.id = id
        super().__init__()

    def start(self):
        self.bus = SocketcanBus(channel=self.channel)
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self.id, txid=self.id+8)
        self.stack = isotp.CanStack(bus=self.bus, address=addr, error_handler=self.error_handler, params=isotp_params)
        super().start()

    def error_handler(self, error):
        logging.warning('IPC IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def stop(self):
        self.bus.shutdown()
        super().stop()

    def shutdown(self):
        self.stop()
        super().shutdown()


class GWM(CanModule):
    def __init__(self, name, channel, id):
        self.name = name
        self.channel = channel
        self.id = id
        super().__init__()

    def start(self):
        self.bus = SocketcanBus(channel=self.channel)
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self.id, txid=self.id+8)
        self.stack = isotp.CanStack(bus=self.bus, address=addr, error_handler=self.error_handler, params=isotp_params)
        super().start()

    def error_handler(self, error):
        logging.warning('GWM IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def stop(self):
        self.bus.shutdown()
        super().stop()

    def shutdown(self):
        self.stop()
        super().shutdown()


class SOBDM(CanModule):
    def __init__(self, name, channel, id):
        self.name = name
        self.channel = channel
        self.id = id
        super().__init__()

    def start(self):
        self.bus = SocketcanBus(channel=self.channel)
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self.id, txid=self.id+8)
        self.stack = isotp.CanStack(bus=self.bus, address=addr, error_handler=self.error_handler, params=isotp_params)
        super().start()

    def error_handler(self, error):
        logging.warning('SOBDM IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def stop(self):
        self.bus.shutdown()
        super().stop()

    def shutdown(self):
        self.stop()
        super().shutdown()


class BCM(CanModule):
    def __init__(self, name, channel, id):
        self.name = name
        self.channel = channel
        self.id = id
        super().__init__()

    def start(self):
        self.bus = SocketcanBus(channel=self.channel)
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self.id, txid=self.id+8)
        self.stack = isotp.CanStack(bus=self.bus, address=addr, error_handler=self.error_handler, params=isotp_params)
        super().start()

    def error_handler(self, error):
        logging.warning('BCM IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def stop(self):
        self.bus.shutdown()
        super().stop()

    def shutdown(self):
        self.stop()
        super().shutdown()


class DCDC(CanModule):
    def __init__(self, name, channel, id):
        self.name = name
        self.channel = channel
        self.id = id
        super().__init__()

    def start(self):
        self.bus = SocketcanBus(channel=self.channel)
        addr = isotp.Address(isotp.AddressingMode.Normal_11bits, rxid=self.id, txid=self.id+8)
        self.stack = isotp.CanStack(bus=self.bus, address=addr, error_handler=self.error_handler, params=isotp_params)
        super().start()

    def error_handler(self, error):
        logging.warning('DCDC IsoTp error happened : %s - %s' % (error.__class__.__name__, str(error)))

    def stop(self):
        self.bus.shutdown()
        super().stop()

    def shutdown(self):
        self.stop()
        super().shutdown()


if __name__ == '__main__':
    apim = GWM('APIM', 'can1', 0x7D0)
    gwm = GWM('GWM', 'can0', 0x716)
    ipc = IPC('GWM', 'can1', 0x720)
    sobdm = SOBDM('SOBDM', 'can0', 0x7E2)
    bcm = BCM('BCM', 'can0', 0x726)
    dcdc = DCDC('DD', 'can0', 0x746)

    apim.start()
    gwm.start()
    ipc.start()
    sobdm.start()
    bcm.start()
    dcdc.start()

    while True:
        try:
            if apim.stack.available():
                payload = apim.stack.recv()
                print("Received APIM payload : %s" % (payload))
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    if pid == 0x8012:
                        alt = 100
                        lat = 2400
                        long = 2400
                        fix = 3
                        speed = 100
                        heading = 256
                        response = struct.pack('>BHHllBHH', 0x62, pid, alt, lat, long, fix, speed, heading)
                    else:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    while apim.stack.transmitting():
                        apim.stack.process()
                        time.sleep(apim.stack.sleep_time())
                    apim.stack.send(response)
            if ipc.stack.available():
                payload = ipc.stack.recv()
                print("Received IPC payload : %s" % (payload))
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    if pid == 0x404C:
                        response = struct.pack('>BHBBB', 0x62, pid, 0x00, 0xDC, 0x66)
                    elif pid == 0x6310:
                        response = struct.pack('>BHB', 0x62, pid, 0)
                    else:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    while ipc.stack.transmitting():
                        ipc.stack.process()
                        time.sleep(ipc.stack.sleep_time())
                    ipc.stack.send(response)
            if gwm.stack.available():
                payload = gwm.stack.recv()
                print("Received GWM payload : %s" % (payload))
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    if pid == 0x411F:
                        response = struct.pack('>BHB', 0x62, pid, 5)
                    else:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    while gwm.stack.transmitting():
                        gwm.stack.process()
                        time.sleep(gwm.stack.sleep_time())
                    gwm.stack.send(response)
            elif sobdm.stack.available():
                payload = sobdm.stack.recv()
                print("Received SOBDM payload : %s" % (payload))
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    if pid == 0xDD00:
                        response = struct.pack('>BHI', 0x62, pid, 0x0923A217)
                    elif pid == 0xDD04:
                        response = struct.pack('>BHB', 0x62, pid, 0x3B)
                    elif pid == 0xDD05:
                        response = struct.pack('>BHB', 0x62, pid, 0x34)
                    elif pid == 0x1E12:
                        response = struct.pack('>BHB', 0x62, pid, 60)
                    else:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    while sobdm.stack.transmitting():
                        sobdm.stack.process()
                        time.sleep(sobdm.stack.sleep_time())
                    sobdm.stack.send(response)
            elif bcm.stack.available():
                payload = bcm.stack.recv()
                print("Received BCM payload : %s" % (payload))
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    if pid == 0x4028:
                        response = struct.pack('>BHB', 0x62, pid, 0x5B)
                    elif pid == 0x402A:
                        response = struct.pack('>BHB', 0x62, pid, 0x92)
                    elif pid == 0x402B:
                        response = struct.pack('>BHB', 0x62, pid, 0x02)
                    elif pid == 0x417D:
                        response = struct.pack('>BHB', 0x62, pid, 0x82)
                    else:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    while bcm.stack.transmitting():
                        bcm.stack.process()
                        time.sleep(bcm.stack.sleep_time())
                    bcm.stack.send(response)
            elif dcdc.stack.available():
                payload = dcdc.stack.recv()
                print("Received DCDC payload : %s" % (payload))
                service, pid = struct.unpack('>BH', payload)
                if service == 0x22:
                    if pid == 0x4836:
                        response = struct.pack('>BHB', 0x62, pid, 0x1B)
                    elif pid == 0x483A:
                        response = struct.pack('>BHB', 0x62, pid, 0x3A)
                    elif pid == 0x483D:
                        response = struct.pack('>BHH', 0x62, pid, 0x0186)
                    else:
                        response = struct.pack('>BBB', 0x7F, 0x22, 0x31)
                    while dcdc.stack.transmitting():
                        dcdc.stack.process()
                        time.sleep(dcdc.stack.sleep_time())
                    dcdc.stack.send(response)

        except KeyboardInterrupt:
            break

    apim.shutdown()
    ipc.shutdown()
    gwm.shutdown()
    sobdm.shutdown()
    bcm.shutdown()
    dcdc.shutdown()
