"""
transport.py

Contains transport layer subclasses of the `TecanAPI` class, which provides
Tecan OEM API frame handling. All subclasses expose instance method `sendRcv`,
which sends a command string (`cmd`) and returns a dictionary containing the
`status_byte` and `data` in the response frame. Current subclasses include:

`TecanAPISerial` : Provides serial encapsulation of TecanAPI frame handling.
                  Can facilitate communication with multiple Tecan devices
                  on the same RS-232 port (i.e., daisy-chaining) by sharing
                  a single serial port instance.

"""

import serial
import uuid
import time
import urllib2

try:
    import simplejson as json
except:
    import json

from time import sleep

from tecanapi import TecanAPI, TecanAPITimeout


class TecanAPISerial(TecanAPI):
    """
    Wraps the TecanAPI class to provide serial communication encapsulation
    and management for the Tecan OEM API. Maps devices to a state-monitored
    dictionary, `ser_mapping`, which allows multiple Tecan devices to
    share a serial port (provided that the serial params are the same).
    """

    ser_mapping = {}

    def __init__(self, tecan_addr, ser_port, ser_baud, ser_timeout=0.1,
                 max_attempts=5):

        super(TecanAPISerial, self).__init__(tecan_addr)

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
        Checks to see if another TecanAPISerial instance has registered the
        same serial port in `ser_mapping`. If there is a conflict, checks to
        see if the parameters match, and if they do, shares the connection.
        Otherwise it raises a `serial.SerialException`.
        """
        reg = TecanAPISerial.ser_mapping
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
                raise serial.SerialException('TecanAPISerial conflict: ' \
                    'another device is already registered to {0} with ' \
                    'different parameters'.format(port))
            else:
                reg[port]['_devices'].append(self.id_)
        self._ser = reg[port]['_ser']

    def __del__(self):
        """
        Cleanup serial port registration on delete
        """
        port_reg = TecanAPISerial.ser_mapping[self.ser_port]
        dev_list = port_reg['_devices']
        ind = dev_list.index(self.id_)
        del dev_list[ind]
        if len(dev_list) == 0:
            port_reg['_ser'].close()
            del port_reg, TecanAPISerial.ser_mapping[self.ser_port]


class TecanAPINode(TecanAPI):
    """
    `TecanAPI` subclass for node-based serial bridge communication.
    Tailored for the ARC GT sequencing platform.
    """

    def __init__(self, tecan_addr, node_addr, response_len=20,
                 max_attempts=5):
        super(TecanAPINode, self).__init__(tecan_addr)
        self.node_addr = node_addr
        self.response_len = response_len
        self.max_attempts = max_attempts

    def sendRcv(self, cmd):
        attempt_num = 0
        while attempt_num < self.max_attempts:
            attempt_num += 1
            if attempt_num == 1:
                frame_out = self.emitFrame(cmd)
            else:
                frame_out = self.emitRepeat()
            url = ('http://{0}/syringe?LENGTH={1}&SYRINGE={2}'
                   ''.format(self.node_addr, self.response_len,
                            frame_out))
            raw_in = self._jsonFetch(url)
            frame_in = self._analyzeFrame(raw_in)
            if frame_in:
                return frame_in
            sleep(0.2 * attempt_num)
        raise(TecanAPITimeout('Tecan HTTP communication exceeded max '
                              'attempts [{0}]'.format(
                              self.max_attempts)))

    #Override _buildFrame for hex encoding
    def _buildFrame(self, repeat=False):
        if repeat:
            seq_byte = int('00111{}'.format(self.SEQ_NUM), 2)
        else:
            seq_byte = int('00110{}'.format(next(self.rotateSeqNum())), 2)
        frame_list = [self.START_BYTE, self.addr, seq_byte] + \
                      self._assembleCmd() + [self.STOP_BYTE]
        checksum = self._buildChecksum(frame_list)
        frame_list.append(checksum)
        return ''.join( [ "%02X" % x for x in frame_list ] )

    #Override _analyzeFrame for hex encoding
    def _analyzeFrame(self, raw_packet):
        data_str = raw_packet['MSG']
        raw_frame = [data_str[i:i+2].decode('hex') for i in\
                     range(0, len(data_str), 2)]
        try:
            # Get basic indices
            frame = raw_frame[raw_frame.index(chr(self.START_BYTE)):
                              raw_frame.index(chr(self.STOP_BYTE))+2]
            if len(frame) < 5:
                return False
            frame_list = [byte for byte in frame]
            int_list = [ord(byte) for byte in frame]
            etx_idx = int_list.index(self.STOP_BYTE)
            data_len = etx_idx - 3
        except:
            return False
        # Integrity checks
        if not frame_list[1] == '0':
            # Master address is always 30h (ASCII 0)
            return False
        if not self._verifyChecksum(int_list):
            return False
        # Dump payload
        if data_len != 0:
            data = ''.join(frame_list[3:etx_idx])
        else:
            data = None
        status_frame = bin(ord(frame_list[2]))[2:].zfill(8)
        payload = {
            'status_byte': status_frame,
            'data': data
        }
        return payload

    def _jsonFetch(self, url):
        fdurl = None
        data = None
        try:
            fdurl = urllib2.urlopen(url)
            data = fdurl.read()
        finally:
            if fdurl:
                fdurl.fp._sock.fp._sock.close() # close the "real" socket later
                fdurl.close()
        if data:
            return json.loads(data)
        else:
            return None
