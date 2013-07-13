import serial
import uuid
import time

# Easily swapped for Gevent sleep
from time import sleep


class TecanAPITimeout(Exception):
    """
    Raised when a Tecan device does not respond to API commands (typically
    after a maximum allowed number of retry attempts has been exceeded)
    """
    pass


class APILink(object):

    def __init__(self, addr):
        self.START_BYTE = 0x02
        self.STOP_BYTE = 0x03
        self.SEQ_NUM = '111'
        self.addr = addr + 0x31  # Add 0x31 to compute hex address equiv.
        self._cmd = 0

    def emitFrame(self, cmd):
        """
        Returns a bytestring outgoing frame built around `cmd`
        """
        self._cmd = cmd
        return self._buildFrame()

    def emitRepeat(self):
        """
        Returns a repeat frame (repeat bit = 1) containing the same `cmd`
        as the previous emitted frame.
        """
        return self._buildFrame(repeat=True)

    def parseFrame(self, frame):
        """
        Parses an incoming frame (bytestring or list). Returns false if the
        frame does not pass validation. Otherwise, returns a dictionary of
        the `status_code` and `data_block`.
        """
        return self._analyzeFrame(frame)

    def _analyzeFrame(self, raw_frame):
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

    def _buildFrame(self, repeat=False):
        if repeat:
            seq_byte = int('00111{}'.format(self.SEQ_NUM), 2)
        else:
            seq_byte = int('00110{}'.format(next(self.rotateSeqNum())), 2)
        frame_list = [self.START_BYTE, self.addr, seq_byte] + \
                      self._assembleCmd() + [self.STOP_BYTE]
        checksum = self._buildChecksum(frame_list)
        frame_list.append(checksum)
        return bytearray(frame_list)

    def _assembleCmd(self):
        """
        Validates the current cmd payload and returns a list of bytes
        generated from the command
        """
        try:
            pack = [int(ord(c)) for c in self._cmd]
            return pack
        except:
            if isinstance(self._cmd, int):
                return [self._cmd]
            else:
                raise TypeError('APILink: command {0} is neither iterable '
                                'nor an int'.format(self._cmd))

    def _buildChecksum(self, partial_frame):
        """
        Builds a checksum based on a partial API frame (frame minus the
        checksum) by XORing the byte values. Returns the checksum as
        an int.

        Args:
            `partial_frame` (list or bytestring) : an assembled api frame
                (with start and end bytes but no checksum)
        """
        checksum = 0
        for byte in partial_frame:
            checksum ^= byte
        return checksum

    def _verifyChecksum(self, frame):
        """
        Verifies a Tecan OEM API checksum (XORed bytes, excluding checksum).

        Args:
            `frame` (list or bytestring) : an assembled or received api frame,
                including the checksum
        """
        partial_frame = frame[:-1]
        checksum = frame[-1]
        if checksum == self._buildChecksum(partial_frame):
            return True
        else:
            return False

    def rotateSeqNum(self):
        """
        Generator function to rotate through possible Tecan API sequence
        numbers 1-7 and output a respective 3 bit str representation
        """
        seq_nums = ['001', '010', '011', '100', '101', '110', '111']
        while True:
            for n in seq_nums:
                self.SEQ_NUM = n
                yield self.SEQ_NUM


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
