import time

try:
    from gevent import monkey; monkey.patch_all(thread=False)
    from gevent import sleep
except:
    from time import sleep


class SyringeError(Exception):
    """
    Error raise when a Cavro pump returns a non-zero error code.

    Args:
        `error_code` (int): the error code returned by the cavro pump
        `error_dict` (dict): dictionary of model-specific error msgs, keyed
                             by error code
    """

    def __init__(self, error_code, error_dict):
        super(SyringeError, self).__init__(self)
        self.err_code = error_code
        try:
            err_str = error_dict[error_code]
            self.err_msg = '{0} [{1}]'.format(err_str, self.err_code)
        except KeyError:
            self.err_msg = 'Unknown Error [{0}]'.format(error_code)

    def __str__(self):
        return self.err_msg


class SyringeTimeout(Exception):
    """ Raised when a syringe wait command times out """
    pass


class Syringe(object):
    """
    General syringe class that may be subclassed for specific syringe models
    or advanced functionality.
    """

    ERROR_DICT = {
        1: 'Initialization Error',
        2: 'Invalid Command',
        3: 'Invalid Operand',
        4: 'Invalid Command Sequence',
        6: 'EEPROM Failure',
        7: 'Device Not Initialized',
        9: 'Plunger Overload',
        10: 'Valve Overload',
        11: 'Plunger Move Not Allowed',
        15: 'Command Overflow'
    }

    def __init__(self, com_link):
        self.com_link = com_link
        self._ready = False
        self._prev_error_code = 0
        self._repeat_error = False

    def _sendRcv(self, cmd_string):
        response = self.com_link.sendRcv(cmd_string)
        ready = self._checkStatus(response['status_byte'])[0]
        data = response['data']
        return data, ready

    def _checkStatus(self, status_byte):
        """
        Parses a bit string representation of a Tecan API status byte for
        potential error codes (and subsequently raises `SyringeError`) and
        returns the status code as a boolean (True = ready, False = busy).

        Defaults to the error code dictionary (`ERROR_DICT`) defined in the
        `Syringe` class; however, this can be overridden in a subclass.

        """
        error_code = int(status_byte[4:8], 2)
        ready = int(status_byte[2])
        if ready == 1:
            self._ready = True
        else:
            self._ready = False
        if error_code == self._prev_error_code:
            self._repeat_error = True
        else:
            self._repeat_error = False
        self._prev_error_code = error_code
        if error_code != 0:
            error_dict = self.__class__.ERROR_DICT
            raise SyringeError(error_code, error_dict)
        return ready, error_code

    def _checkReady(self):
        """
        Checks to see if the syringe is ready to accept a new command (i.e.
        is not busy). Returns `True` if it is ready, or `False` if it is not.

        """
        if self._ready:
            return True
        try:
            ready = self._sendRcv('Q')[1]
            return ready
        except SyringeError as e:
            if self._repeat_error:
                return self._ready
            else:
                raise e

    def _waitReady(self, polling_interval=0.3, timeout=10, delay=None):
        """
        Waits for the syringe to be ready to accept a command

        Kwargs:
            `polling_interval` (int): frequency of polling in seconds
            `timeout` (int): max wait time in seconds

        """
        if delay:
            sleep(delay)
        start = time.time()
        while (start-time.time()) < (start+timeout):
            ready = self._checkReady()
            if not ready:
                sleep(polling_interval)
            else:
                return
        raise(SyringeTimeout('Timeout while waiting for syringe to be ready'
                             ' to accept commands [{}]'.format(timeout)))
