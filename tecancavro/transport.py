"""
transport.py

Contains transport layer subclasses of the `APILink` class, which provides
Tecan OEM API frame handling. All subclasses expose instance method `sendRcv`,
which sends a command string (`cmd`) and returns a dictionary containing the
`status_byte` and `data` in the response frame. Current subclasses include:

`SerialAPILink` : Provides serial encapsulation of TecanAPI frame handling.
                  Can facilitate communication with multiple Tecan devices
                  on the same RS-232 port (i.e., daisy-chaining) by sharing
                  a single serial port instance.

"""

import serial
import uuid
import time

from time import sleep

from tecanapi import APILink


class TecanAPITimeout(Exception):
    """
    Raised when a Tecan device does not respond to API commands (typically
    after a maximum allowed number of retry attempts has been exceeded)
    """
    pass


class SerialAPILink(APILink):
    """
    Wraps the APILink class to provide serial communication encapsulation
    and management for the Tecan OEM API. Maps devices to a state-monitored
    dictionary, `ser_mapping`, which allows multiple Tecan devices to
    share a serial port (provided that the serial params are the same).
    """

    ser_mapping = {}

    def __init__(self, addr, ser_port, ser_baud, ser_timeout=0.1,
                 max_attempts=5):

        super(SerialAPILink, self).__init__(addr)

        self.id_ = str(uuid.uuid4())
        self.ser_port = ser_port
        self.ser_info = {
            'baud': ser_baud,
            'timeout': ser_timeout,
            'max_attempts': max_attempts
        }
        self._registerSer()

    def sendRcv(self, cmd):
        attempt_num = 0
        while attempt_num < self.ser_info['max_attempts']:
            try:
                attempt_num += 1
                if attempt_num == 1:
                    frame_out = self.emitFrame(cmd)
                else:
                    frame_out = self.emitRepeat()
                self._sendFrame(frame_out)
                frame_in = self._receiveFrame()
                if frame_in:
                    return frame_in
                sleep(0.05 * attempt_num)
            except serial.SerialException:
                sleep(0.2)
        raise(TecanAPITimeout('Tecan serial communication exceeded max '
                              'attempts [{0}]'.format(
                              self.ser_info['max_attempts'])))

    def _sendFrame(self, frame):
        self._ser.write(frame)

    def _receiveFrame(self):
        raw_data = self._ser.readline()
        return self.parseFrame(raw_data.rstrip('\n'))

    def _registerSer(self):
        """
        Checks to see if another SerialAPILink instance has registered the
        same serial port in `ser_mapping`. If there is a conflict, checks to
        see if the parameters match, and if they do, shares the connection.
        Otherwise it raises a `serial.SerialException`.
        """
        reg = SerialAPILink.ser_mapping
        port = self.ser_port
        if self.ser_port not in reg:
            reg[port] = {}
            reg[port]['info'] = {k: v for k, v in self.ser_info.iteritems()}
            reg[port]['_ser'] = serial.Serial(port=port,
                                              baudrate=reg[port]['info']['baud'],
                                              timeout=reg[port]['info']['timeout'])
            reg[port]['_devices'] = [self.id_]
        else:
            if len(set(self.ser_info.items()) &
               set(reg[port]['info'].items())) != 3:
                raise serial.SerialException('SerialAPILink conflict: ' \
                    'another device is already registered to {0} with ' \
                    'different parameters'.format(port))
            else:
                reg[port]['_devices'].append(self.id_)
        self._ser = reg[port]['_ser']

    def __del__(self):
        """
        Cleanup serial port registration on delete
        """
        port_reg = SerialAPILink.ser_mapping[self.ser_port]
        dev_list = port_reg['_devices']
        ind = dev_list.index(self.id_)
        del dev_list[ind]
        if len(dev_list) == 0:
            port_reg['_ser'].close()
            del port_reg, SerialAPILink.ser_mapping[self.ser_port]
