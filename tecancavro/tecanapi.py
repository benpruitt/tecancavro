"""
tecanapi.py

Contains the `TecanAPI` class to facilitate device communication over
the Tecan OEM API. The `TecanAPI` class provides bare-bones API frame
construction and parsing, and may be subclassed to provide transport-
layer encapsulation (e.g. serial encasulation).

"""


class TecanAPITimeout(Exception):
    """
    Raised when a Tecan device does not respond to API commands (typically
    after a maximum allowed number of retry attempts has been exceeded)
    """
    pass


class TecanAPI(object):

    def __init__(self, addr):
        self.START_BYTE = 0x02
        self.STOP_BYTE = 0x03
        self.SEQ_NUM = b'111'
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
            raw_frame = bytearray(raw_frame)
            frame_list = [byte for byte in raw_frame]
            frame = frame_list[
                frame_list.index(self.START_BYTE):
                frame_list.index(self.STOP_BYTE)+2]
            if len(frame) < 5:
                return False
            frame_list = [byte for byte in frame]
            etx_idx = frame_list.index(self.STOP_BYTE)
            data_len = etx_idx - 3
        except ValueError:
            return False
        # Integrity checks
        if not self._verifyChecksum(frame_list):
            return False
        # Dump payload
        if data_len != 0:
            data = b''.join([chr(i).encode('utf-8') for i in
                             frame_list[3:etx_idx]])
        else:
            data = None
        status_frame = '{:08b}'.format(frame_list[2])
        payload = {
            'status_byte': status_frame,
            'data': data
        }
        return payload

    def _buildFrame(self, repeat=False):
        if repeat:
            seq_byte = int(b'00111' + self.SEQ_NUM, 2)
        else:
            seq_byte = int(b'00110' + next(self.rotateSeqNum()), 2)
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
                raise TypeError('TecanAPI: command {0} is neither iterable '
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
        seq_nums = [b'001', b'010', b'011', b'100', b'101', b'110', b'111']
        while True:
            for n in seq_nums:
                self.SEQ_NUM = n
                yield self.SEQ_NUM
