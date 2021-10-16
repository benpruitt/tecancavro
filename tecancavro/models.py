"""
models.py

Contains Tecan Cavro model-specific classes that inherit from the `Syringe`
class in syringe.py.

Current models:

    XCaliburD (distributor valve)
    XCalibur (Non-distributor valve)
    XE1000

"""
import time
import logging

from math import sqrt
from time import sleep
from functools import wraps
from contextlib import contextmanager

try:
    from gevent import monkey; monkey.patch_all(thread=False)
    from gevent import sleep
except:
    from time import sleep

from .syringe import Syringe, SyringeError, SyringeTimeout

#############################################################################
#############################################################################
##                                                                         ##
##                Tecan XCalibur Syringe Pump Distributor valve            ##
##                                                                         ##
#############################################################################
#############################################################################

class XCaliburD(Syringe):
    """
    Class to control XCalibur pumps with distribution valves. Provides front-
    end validation and convenience functions (e.g. smartExtract) -- see
    individual docstrings for more information.
    """

    DIR_DICT = {'CW': ('I', 'Z'), 'CCW': ('O', 'Y')}

    SPEED_CODES = {0: 6000, 1: 5600, 2: 5000, 3: 4400, 4: 3800, 5: 3200,
                   6: 2600, 7: 2200, 8: 2000, 9: 1800, 10: 1600, 11: 1400,
                   12: 1200, 13: 1000, 14: 800, 15: 600, 16: 400, 17: 200,
                   18: 190, 19: 180, 20: 170, 21: 160, 22: 150, 23: 140,
                   24: 130, 25: 120, 26: 110, 17: 100, 28: 90, 29: 80,
                   30: 70, 31: 60, 32: 50, 33: 40, 34: 30, 35: 20, 36: 18,
                   37: 16, 38: 14, 39: 12, 40: 10}

    def __init__(self, com_link, num_ports=9, syringe_ul=1000, direction='CW',
                 microstep=False, waste_port=9, slope=14, init_force=0,
                 debug=False, debug_log_path='.'):
        """
        Object initialization function.
        Args:
            `com_link` (Object) : instantiated TecanAPI subclass / transport
                                  layer (see transport.py)
                *Must have a `.sendRcv(cmd)` instance method to send a command
                    string and parse the reponse (see transport.py)
        Kwargs:
            `num_ports` (int) : number of ports on the distribution valve
                [default] - 9
            `syringe_ul` (int) : syringe volume in microliters
                [default] - 1000
            `microstep` (bool) : whether or not to operate in microstep mode
                [default] - False (factory default)
            `waste_port` (int) : waste port for `extractToWaste`-like
                                 convenience functions
                [default] - 9 (factory default for init out port)
            `slope` (int) : slope setting
                [default] - 14 (factory default)
            `init_force` (int) : initialization force or speed
                0 [default] - full plunger force and default speed
                1 - half plunger force and default speed
                2 - one third plunger force and default speed
                10-40 - full force and speed code X
            `debug` (bool) : turns on debug file, which logs extensive debug
                             output to 'xcaliburd_debug.log' at
                             `debug_log_path`
                [default] - False
            `debug_log_path` : path to debug log file - only relevant if
                               `debug` == True.
                [default] - '' (cwd)
        """
        super(XCaliburD, self).__init__(com_link)
        self.num_ports = num_ports
        self.syringe_ul = syringe_ul
        self.direction = direction
        self.waste_port = waste_port
        self.init_force = init_force
        self.state = {
            'plunger_pos': None,
            'port': None,
            'microstep': microstep,
            'start_speed': None,
            'top_speed': None,
            'cutoff_speed': None,
            'slope': slope
        }

        # Handle debug mode init
        self.debug = debug
        if self.debug:
            self.initDebugLogging(debug_log_path)

        self.setMicrostep(on=microstep)

        # Command chaining state information
        self.cmd_chain = ''
        self.exec_time = 0
        self.sim_speed_change = False
        self.sim_state = {k: v for k, v in self.state.items()}

        # Init functions
        self.updateSpeeds()
        self.getPlungerPos()
        self.getCurPort()
        self.updateSimState()

    #########################################################################
    # Debug functions                                                       #
    #########################################################################

    def initDebugLogging(self, debug_log_path):
        """ Initialize logger and log file handler """

        self.logger = logging.getLogger('XCaliburD')
        fp = debug_log_path.rstrip('/') + '/xcaliburd_debug.log'
        hdlr = logging.FileHandler(fp)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)

    def logCall(self, f_name, f_locals):
        """ Logs function params at call """

        if self.debug:
            self.logger.debug('-> {}: {}'.format(f_name, f_locals))

    def logDebug(self, msg):
        """ Handles debug logging if self.debug == True """

        if self.debug:
            self.logger.debug(msg)

    #########################################################################
    # Pump initialization                                                   #
    #########################################################################

    def init(self, init_force=None, direction=None, in_port=None,
             out_port=None):
        """
        Initialize pump. Uses instance `self.init_force` and `self.direction`
        if not provided. Blocks until initialization is complete.
        """
        self.logCall('init', locals())

        init_force = init_force if init_force is not None else self.init_force
        direction = direction if direction is not None else self.direction
        out_port = out_port if out_port is not None else self.waste_port
        in_port = in_port if in_port is not None else 0

        cmd_string = '{0}{1},{2},{3}'.format(
                     self.__class__.DIR_DICT[direction][1],
                     init_force, in_port, out_port)
        self.sendRcv(cmd_string, execute=True)
        self.waitReady()
        return 0  # 0 seconds left to wait

    #########################################################################
    # Convenience functions                                                 #
    #########################################################################

    def extractToWaste(self, in_port, volume_ul, out_port=None,
                       speed_code=None, minimal_reset=False, flush=False):
        """
        Extracts `volume_ul` from `in_port`. If the relative plunger move
        exceeds the encoder range, the syringe will dispense to `out_port`,
        which defaults to `self.waste_port`. If `minimal_reset` is `True`,
        state updates upon execution will be based on simulations rather
        than polling. If `flush` is `True`, the contents of the syringe
        will be flushed to waste following the extraction.
        """
        self.logCall('extractToWaste', locals())

        out_port = out_port if out_port is not None else self.waste_port
        if speed_code is not None:
            self.setSpeed(speed_code)
        self.cacheSimSpeeds()
        steps = self._ulToSteps(volume_ul)

        retry = False
        extracted = False

        while not extracted:
            try:
                # If the move is calculated to execeed 3000 encoder counts,
                # dispense to waste and then make relative plunger extract
                if (self.sim_state['plunger_pos'] + steps) > 3000 or retry:
                    self.logDebug('extractToWaste: move would exceed 3000 '
                                  'dumping to out port [{}]'.format(out_port))
                    self.changePort(out_port, from_port=in_port)
                    self.setSpeed(0)
                    self.movePlungerAbs(0)
                    self.changePort(in_port, from_port=out_port)
                    self.restoreSimSpeeds()
                # Make relative plunger extract
                self.changePort(in_port)
                self.logDebug('extractToWaste: attempting relative extract '
                              '[steps: {}]'.format(steps))
                # Delay execution 200 ms to stop oscillations
                self.delayExec(200)
                self.movePlungerRel(steps)
                if flush:
                    self.dispenseToWaste()
                exec_time = self.executeChain(minimal_reset=True)
                extracted = True
            except SyringeError as e:
                if e.err_code in [2, 3, 4]:
                    self.logDebug('extractToWaste: caught SyringeError [{}], '
                                  'retrying.')
                    retry = True
                    self.resetChain()
                    self.waitReady()
                    continue
                else:
                    raise
        return exec_time

    def primePort(self, in_port, volume_ul, speed_code=None, out_port=None,
                  split_command=False):
        """
        Primes the line on `in_port` with `volume_ul`, which can
        exceed the maximum syringe volume. If `speed_code` is
        provided, the syringe speed will be appended to the
        beginning of the command chain. Blocks until priming is complete.
        """
        self.logCall('primePort', locals())

        if out_port is None:
            out_port = self.waste_port
        if speed_code is not None:
            self.setSpeed(speed_code)
        if volume_ul > self.syringe_ul:
            num_rounds = volume_ul / self.syringe_ul
            remainder_ul = volume_ul % self.syringe_ul
            self.changePort(out_port, from_port=in_port)
            self.movePlungerAbs(0)
            for x in xrange(num_rounds):
                self.changePort(in_port, from_port=out_port)
                self.movePlungerAbs(3000)
                self.changePort(out_port, from_port=in_port)
                self.movePlungerAbs(0)
                delay = self.executeChain()
                self.waitReady(delay)
            if remainder_ul != 0:
                self.changePort(in_port, from_port=out_port)
                self.movePlungerAbs(self._ulToSteps(remainder_ul))
                self.changePort(out_port, from_port=in_port)
                self.movePlungerAbs(0)
                delay = self.executeChain()
                self.waitReady(delay)
        else:
            self.changePort(out_port)
            self.movePlungerAbs(0)
            self.changePort(in_port, from_port=out_port)
            self.movePlungerAbs(self._ulToSteps(volume_ul))
            self.changePort(out_port, from_port=in_port)
            self.movePlungerAbs(0)
            delay = self.executeChain()
            self.waitReady(delay)

    #########################################################################
    # Command chain functions                                               #
    #########################################################################

    def executeChain(self, minimal_reset=False):
        """
        Executes and resets the current command chain (`self.cmd_chain`).
        Returns the estimated execution time (`self.exec_time`) for the chain.
        """
        self.logCall('executeChain', locals())

        # Compensaate for reset time (tic/toc) prior to returning wait_time
        tic = time.time()
        self.sendRcv(self.cmd_chain, execute=True)
        exec_time = self.exec_time
        self.resetChain(on_execute=True, minimal_reset=minimal_reset)
        toc = time.time()
        wait_time = exec_time - (toc-tic)
        if wait_time < 0:
            wait_time = 0
        return wait_time

    def resetChain(self, on_execute=False, minimal_reset=False):
        """
        Resets the command chain (`self.cmd_chain`) and execution time
        (`self.exec_time`). Optionally updates `slope` and `microstep`
        state variables, speeds, and simulation state.
        Kwargs:
            `on_execute` (bool) : should be used to indicate whether or not
                                  the chain being reset was executed, which
                                  will cue slope and microstep state
                                  updating (as well as speed updating).
            `minimal_reset` (bool) : minimizes additional polling of the
                                     syringe pump and updates state based
                                     on simulated calculations. Should
                                     be extremely reliable but use with
                                     caution.
        """
        self.logCall('resetChain', locals())

        self.cmd_chain = ''
        self.exec_time = 0
        if (on_execute and self.sim_speed_change):
            if minimal_reset:
                self.state = {k: v for k, v in self.sim_state.items()}
            else:
                self.state['slope'] = self.sim_state['slope']
                self.state['microstep'] = self.sim_state['microstep']
                self.updateSpeeds()
                self.getCurPort()
                self.getPlungerPos()
        self.sim_speed_change = False
        self.updateSimState()

    def updateSimState(self):
        """
        Copies the current state dictionary (`self.state`) to the
        simulation state dictionary (`self.sim_state`)
        """
        self.logCall('updateSimState', locals())

        self.sim_state = {k: v for k, v in self.state.items()}

    def cacheSimSpeeds(self):
        """
        Caches the simulation state speed settings when called. May
        be used for convenience functions in which speed settings
        need to be temporarily changed and then reverted
        """
        self.logCall('cacheSimSpeeds', locals())

        self._cached_start_speed = self.sim_state['start_speed']
        self._cached_top_speed = self.sim_state['top_speed']
        self._cached_cutoff_speed = self.sim_state['cutoff_speed']

    def restoreSimSpeeds(self):
        """ Restores simulation speeds cached by `self.cacheSimSpeeds` """
        self.logCall('restoreSimSpeeds', locals())

        self.sim_state['start_speed'] = self._cached_start_speed
        self.sim_state['top_speed'] = self._cached_top_speed
        self.sim_state['cutoff_speed'] = self._cached_cutoff_speed
        self.setTopSpeed(self._cached_top_speed)
        if 50 <= self._cached_start_speed <= 1000:
            self.setStartSpeed(self._cached_start_speed)
        if 50 <= self._cached_cutoff_speed <= 2700:
            self.setCutoffSpeed(self._cached_cutoff_speed)

    def execWrap(func):
        """
        Decorator to wrap chainable commands, allowing for immediate execution
        of the wrapped command by passing in an `execute=True` kwarg.
        """
        @wraps(func)
        def addAndExec(self, *args, **kwargs):
            execute = False
            if 'execute' in kwargs:
                execute = kwargs.pop('execute')
            if 'minimal_reset' in kwargs:
                minimal_reset = kwargs.pop('minimal_reset')
            else:
                minimal_reset = False
            func(self, *args, **kwargs)
            if execute:
                return self.executeChain(minimal_reset=minimal_reset)
        return addAndExec

    #########################################################################
    # Chainable high level functions                                        #
    #########################################################################

    @execWrap
    def dispenseToWaste(self, retain_port=True):
        """
        Dispense current syringe contents to waste. If `retain_port` is true,
        the syringe will be returned to the original port after the dump.
        """
        self.logCall('dispenseToWaste', locals())
        if retain_port:
            orig_port = self.sim_state['port']
        self.changePort(self.waste_port)
        self.movePlungerAbs(0)
        if retain_port:
            self.changePort(orig_port)

    @execWrap
    def extract(self, from_port, volume_ul):
        """ Extract `volume_ul` from `from_port` """
        self.logCall('extract', locals())

        steps = self._ulToSteps(volume_ul)
        self.changePort(from_port)
        self.movePlungerRel(steps)

    @execWrap
    def dispense(self, to_port, volume_ul):
        """ Dispense `volume_ul` from `to_port` """
        self.logCall('dispense', locals())

        steps = self._ulToSteps(volume_ul)
        self.changePort(to_port)
        self.movePlungerRel(-steps)

    #########################################################################
    # Chainable low level functions                                         #
    #########################################################################

    @execWrap
    def changePort(self, to_port, from_port=None, direction='CW'):
        """
        Change port to `to_port`. If `from_port` is provided, the `direction`
        will be calculated to minimize travel time. `direction` may also be
        provided directly.
        Args:
            `to_port` (int) : port to which to change
        Kwargs:
            `from_port` (int) : originating port
            `direction` (str) : direction of valve movement
                'CW' - clockwise
                'CCW' - counterclockwise
        """
        self.logCall('changePort', locals())

        if not 0 < to_port <= self.num_ports:
            raise(ValueError('`to_port` [{0}] must be between 1 and '
                             '`num_ports` [{1}]'.format(to_port,
                                                        self.num_ports)))
        if not from_port:
            if self.sim_state['port']:
                from_port = self.sim_state['port']
            else:
                from_port = 1
        delta = to_port - from_port
        diff = -delta if abs(delta) >= 7 else delta
        direction = 'CCW' if diff < 0 else 'CW'
        cmd_string = '{0}{1}'.format(self.__class__.DIR_DICT[direction][0],
                                     to_port)
        self.sim_state['port'] = to_port
        self.cmd_chain += cmd_string
        self.exec_time += 0.2

    @execWrap
    def movePlungerAbs(self, abs_position):
        """
        Moves the plunger to absolute position `abs_position`
        Args:
            `abs_position` (int) : absolute plunger position
                (0-24000) in microstep mode
                (0-3000) in standard mode
        """
        self.logCall('movePlungerAbs', locals())

        if self.sim_state['microstep']:
            if not 0 <= abs_position <= 24000:
                raise(ValueError('`abs_position` must be between 0 and 24000'
                                 ' when operating in microstep mode'
                                 ''.format(self.port_num)))
        else:
            if not 0 <= abs_position <= 3000:
                raise(ValueError('`abs_position` must be between 0 and 3000'
                                 ' when operating in standard mode'
                                 ''.format(self.port_num)))
        cmd_string = 'A{0}'.format(abs_position)
        cur_pos = self.sim_state['plunger_pos']
        delta_pos = cur_pos-abs_position
        self.sim_state['plunger_pos'] = abs_position
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(delta_pos))

    @execWrap
    def movePlungerRel(self, rel_position):
        """
        Moves the plunger to relative position `rel_position`. There is no
        front-end error handling -- invalid relative moves will result in
        error code 3 from the XCalibur, raising a `SyringeError`
        Args:
            `rel_position` (int) : relative plunger position
                if rel_position < 0 : plunger moves up (relative dispense)
                if rel_position > 0 : plunger moves down (relative extract)
        """
        self.logCall('movePlungerRel', locals())

        if rel_position < 0:
            cmd_string = 'D{0}'.format(abs(rel_position))
        else:
            cmd_string = 'P{0}'.format(rel_position)
        self.sim_state['plunger_pos'] += rel_position
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(rel_position))

    #########################################################################
    # Command set commands                                                  #
    #########################################################################

    @execWrap
    def setSpeed(self, speed_code):
        """ Set top speed by `speed_code` (see OEM docs) """
        self.logCall('setSpeed', locals())

        if not 0 <= speed_code <= 40:
            raise(ValueError('`speed_code` [{0}] must be between 0 and 40'
                             ''.format(speed_code)))
        cmd_string = 'S{0}'.format(speed_code)
        self.sim_speed_change = True
        self._simIncToPulses(speed_code)
        self.cmd_chain += cmd_string

    @execWrap
    def setStartSpeed(self, pulses_per_sec):
        """ Set start speed in `pulses_per_sec` [50-1000] """
        self.logCall('setStartSpeed', locals())

        cmd_string = 'v{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setTopSpeed(self, pulses_per_sec):
        """ Set top speed in `pulses_per_sec` [5-6000] """
        self.logCall('setTopSpeed', locals())

        cmd_string = 'V{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setCutoffSpeed(self, pulses_per_sec):
        """ Set cutoff speed in `pulses_per_sec` [50-2700] """
        self.logCall('setCutoffSpeed', locals())

        cmd_string = 'c{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setSlope(self, slope_code, chain=False):
        self.logCall('setSlope', locals())

        if not 1 <= slope_code <= 20:
            raise(ValueError('`slope_code` [{0}] must be between 1 and 20'
                             ''.format(slope_code)))
        cmd_string = 'L{0}'.format(slope_code)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    # Chainable control commands

    @execWrap
    def repeatCmdSeq(self, num_repeats):
        self.logCall('repeatCmdSeq', locals())

        if not 0 < num_repeats < 30000:
            raise(ValueError('`num_repeats` [{0}] must be between 0 and 30000'
                             ''.format(num_repeats)))
        cmd_string = 'G{0}'.format(num_repeats)
        self.cmd_chain += cmd_string
        self.exec_time *= num_repeats

    @execWrap
    def markRepeatStart(self):
        self.logCall('markRepeatStart', locals())

        cmd_string = 'g'
        self.cmd_chain += cmd_string

    @execWrap
    def delayExec(self, delay_ms):
        """ Delays command execution for `delay` milliseconds """
        self.logCall('delayExec', locals())

        if not 0 < delay_ms < 30000:
            raise(ValueError('`delay` [{0}] must be between 0 and 40000 ms'
                             ''.format(delay_ms)))
        cmd_string = 'M{0}'.format(delay_ms)
        self.cmd_chain += cmd_string

    @execWrap
    def haltExec(self, input_pin=0):
        """
        Used within a command string to halt execution until another [R]
        command is sent, or until TTL pin `input_pin` goes low
        Kwargs:
            `input_pin` (int) : input pin code corresponding to the desired
                                TTL input signal pin on the XCalibur
                0 - either 1 or 2
                1 - input 1 (J4 pin 7)
                2 - input 2 (J4 pin 8)
        """
        self.logCall('haltExec', locals())

        if not 0 <= input_pin < 2:
            raise(ValueError('`input_pin` [{0}] must be between 0 and 2'
                             ''.format(input_sig)))
        cmd_string = 'H{0}'.format(input_sig)
        return self.sendRcv(cmd_string)

    #########################################################################
    # Report commands (cannot be chained)                                   #
    #########################################################################

    def updateSpeeds(self):
        self.logCall('updateSpeeds', locals())

        self.getStartSpeed()
        self.getTopSpeed()
        self.getCutoffSpeed()

    def getPlungerPos(self):
        """ Returns the absolute plunger position as an int (0-3000) """
        self.logCall('getPlungerPos', locals())

        cmd_string = '?'
        data = self.sendRcv(cmd_string)
        self.state['plunger_pos'] = int(data)
        return self.state['plunger_pos']

    def getStartSpeed(self):
        """ Returns the start speed as an int (in pulses/sec) """
        self.logCall('getStartSpeed', locals())

        cmd_string = '?1'
        data = self.sendRcv(cmd_string)
        self.state['start_speed'] = int(data)
        return self.state['start_speed']

    def getTopSpeed(self):
        """ Returns the top speed as an int (in pulses/sec) """
        self.logCall('getTopSpeed', locals())

        cmd_string = '?2'
        data = self.sendRcv(cmd_string)
        self.state['top_speed'] = int(data)
        return self.state['top_speed']

    def getCutoffSpeed(self):
        """ Returns the cutoff speed as an int (in pulses/sec) """
        self.logCall('getCutoffSpeed', locals())

        cmd_string = '?3'
        data = self.sendRcv(cmd_string)
        self.state['cutoff_speed'] = int(data)
        return self.state['cutoff_speed']

    def getEncoderPos(self):
        """ Returns the current encoder count on the plunger axis """
        self.logCall('getEncoderPos', locals())

        cmd_string = '?4'
        data = self.sendRcv(cmd_string)
        return int(data)

    def getCurPort(self):
        """ Returns the current port position (1-num_ports) """
        self.logCall('getCurPort', locals())

        cmd_string = '?6'
        data = self.sendRcv(cmd_string)
        with self._syringeErrorHandler():
            try:
                port = int(data)
            except ValueError:
                raise SyringeError(7, self.__class__.ERROR_DICT)
            self.state['port'] = port
            return port

    def getBufferStatus(self):
        """ Returns the current cmd buffer status (0=empty, 1=non-empty) """
        self.logCall('getBufferStatus', locals())

        cmd_string = '?10'
        data = self.sendRcv(cmd_string)
        return int(data)

    #########################################################################
    # Config commands                                                       #
    #########################################################################

    def setMicrostep(self, on=False):
        """ Turns microstep mode on or off """
        self.logCall('setMicrostep', locals())

        cmd_string = 'N{0}'.format(int(on))
        self.sendRcv(cmd_string, execute=True)
        self.microstep = on

    #########################################################################
    # Control commands                                                      #
    #########################################################################

    def terminateCmd(self):
        self.logCall('terminateCommand', locals())

        cmd_string = 'T'
        return self.sendRcv(cmd_string, execute=True)

    #########################################################################
    # Communication handlers and special functions                          #
    #########################################################################

    @contextmanager
    def _syringeErrorHandler(self):
        """
        Context manager to handle `SyringeError` based on error code. Right
        now this just handles error codes 7, 9, and 10 by initializing the
        pump and then re-running the previous command.
        """
        try:
            yield
        except SyringeError as e:
            self.logDebug('ErrorHandler: caught error code {}'.format(
                          e.err_code))
            if e.err_code in [7, 9, 10]:
                last_cmd = self.last_cmd
                self.resetChain()
                try:
                    self.logDebug('ErrorHandler: attempting re-init')
                    self.init()
                except SyringeError as e:
                    self.logDebug('ErrorHandler: Error during re-init '
                                  '[{}]'.format(e.err_code))
                    if e.err_code in [7, 9, 10]:
                        pass
                    else:
                        raise e
                self._waitReady()
                self.logDebug('ErrorHandler: resending last command {} '
                              ''.format(last_cmd))
                self.sendRcv(last_cmd)
            else:
                self.logDebug('ErrorHandler: error not in [7, 9, 10], '
                              're-raising [{}]'.format(e.err_code))
                self.resetChain()
                raise e
        except Exception as e:
            self.resetChain()
            raise e

    def waitReady(self, timeout=10, polling_interval=0.3, delay=None):
        """
        Waits a maximum of `timeout` seconds for the syringe to be
        ready to accept another set command, polling every `polling_interval`
        seconds. If a `delay` is provided, the function will sleep `delay`
        seconds prior to beginning polling.
        """
        self.logCall('waitReady', locals())
        with self._syringeErrorHandler():
            self._waitReady(timeout=timeout, polling_interval=polling_interval,
                            delay=delay)

    def sendRcv(self, cmd_string, execute=False):
        """
        Send a raw command string and return a tuple containing the parsed
        response data: (Data, Ready). If the syringe is ready to accept
        another command, `Ready` with be 'True'.
        Args:
            `cmd_string` (bytestring) : a valid Tecan XCalibur command string
        Kwargs:
            `execute` : if 'True', the execute byte ('R') is appended to the
                        `cmd_string` prior to sending
        Returns:
            `parsed_reponse` (tuple) : parsed pump response tuple
        """
        self.logCall('sendRcv', locals())

        if execute:
            cmd_string += 'R'
        self.last_cmd = cmd_string
        self.logDebug('sendRcv: sending cmd_string: {}'.format(cmd_string))
        with self._syringeErrorHandler():
            parsed_response = super(XCaliburD, self)._sendRcv(cmd_string)
            self.logDebug('sendRcv: received response: {}'.format(
                          parsed_response))
            data = parsed_response[0]
            return data

    def _calcPlungerMoveTime(self, move_steps):
        """
        Calculates plunger move time using equations provided by Tecan.
        Assumes that all input values have been validated
        """
        sd = self.sim_state
        start_speed = sd['start_speed']
        top_speed = sd['top_speed']
        cutoff_speed = sd['cutoff_speed']
        slope = sd['slope']
        microstep = sd['microstep']

        slope *= 2500.0
        if microstep:
            move_steps = move_steps / 8.0
        theo_top_speed = sqrt((4.0 * move_steps*slope) + start_speed ** 2.0)
        # If theoretical top speed will not exceed cutoff speed
        if theo_top_speed < cutoff_speed:
            move_t = theo_top_speed - (start_speed/slope)
        else:
            theo_top_speed = sqrt(((2.0*move_steps*slope) +
                                  ((start_speed**2.0+cutoff_speed**2.0)/2.0)))
        # If theoretical top speed with exceed cutoff speed but not
        # reach the set top speed
        if cutoff_speed < theo_top_speed < top_speed:
            move_t = ((1 / slope) * (2.0 * theo_top_speed - start_speed -
                                     cutoff_speed))
        # If start speed, top speed, and cutoff speed are all the same
        elif start_speed == top_speed == cutoff_speed:
            move_t = (2.0 * move_steps) / top_speed
        # Otherwise, calculate time spent in each phase (start, constant,
        # ramp down)
        else:
            ramp_up_halfsteps = ((top_speed ** 2.0 - start_speed ** 2.0) /
                                (2.0 * slope))
            ramp_down_halfsteps = ((top_speed ** 2.0 - cutoff_speed ** 2.0) /
                                  (2.0 * slope))
            if (ramp_up_halfsteps + ramp_down_halfsteps) < (2.0 * top_speed):
                ramp_up_t = (top_speed - start_speed) / slope
                ramp_down_t = (top_speed - cutoff_speed) / slope
                constant_halfsteps = (2.0 * move_steps - ramp_up_halfsteps -
                                      ramp_down_halfsteps)
                constant_t = constant_halfsteps / top_speed
                move_t = ramp_up_t + ramp_down_t + constant_t
        return move_t

    def _ulToSteps(self, volume_ul, microstep=None):
        """
        Converts a volume in microliters (ul) to encoder steps.
        Args:
            `volume_ul` (int) : volume in microliters
        Kwargs:
            `microstep` (bool) : whether to convert to standard steps or
                                 microsteps
        """
        if microstep is None:
            microstep = self.state['microstep']
        if microstep:
            steps = volume_ul * (24000/self.syringe_ul)
        else:
            steps = volume_ul * (3000/self.syringe_ul)
        return steps

    def _simIncToPulses(self, speed_inc):
        """
        Updates simulation speeds given a speed increment setting (`speed_inc`)
        following XCalibur handling of speed changes (i.e. cutoff speed cannot
        be higher than top speed, so it is automatically adjusted on the pump)
        """
        top_speed = self.__class__.SPEED_CODES[speed_inc]
        self.sim_state['top_speed'] = top_speed
        if self.sim_state['start_speed'] > top_speed:
            self.sim_state['start_speed'] = top_speed
        if self.sim_state['cutoff_speed'] > top_speed:
            self.sim_state['cutoff_speed'] = top_speed


#############################################################################
#############################################################################
##                                                                         ##
##                Tecan XCalibur Syringe Pump Non-distributor valve        ##
##                                                                         ##
#############################################################################
#############################################################################


class XCalibur(Syringe):
    """
    Class to control XCalibur pumps with non-distribution valves. Provides 
    front end validation and convenience functions -- see individual 
    docstrings for more information.
    """

    SPEED_CODES = {0: 6000, 1: 5600, 2: 5000, 3: 4400, 4: 3800, 5: 3200,
                   6: 2600, 7: 2200, 8: 2000, 9: 1800, 10: 1600, 11: 1400,
                   12: 1200, 13: 1000, 14: 800, 15: 600, 16: 400, 17: 200,
                   18: 190, 19: 180, 20: 170, 21: 160, 22: 150, 23: 140,
                   24: 130, 25: 120, 26: 110, 27: 100, 28: 90, 29: 80,
                   30: 70, 31: 60, 32: 50, 33: 40, 34: 30, 35: 20, 36: 18,
                   37: 16, 38: 14, 39: 12, 40: 10}

    REVERSE_SPEED_CODES = {v: k for k, v in SPEED_CODES.items()}

    def __init__(self, com_link, syringe_ul=2500, direction='Z',
                 microstep=False, slope=14, speed=16,
                 debug=False, debug_log_path='.'):
        """
        Object initialization function.

        Args:
            `com_link` (Object) : instantiated TecanAPI subclass / transport
                                  layer (see transport.py)
                *Must have a `.sendRcv(cmd)` instance method to send a command
                    string and parse the reponse (see transport.py)
        Kwargs:
            `syringe_ul` (int) : syringe volume in microliters
                [default] - 2500
            `direction` (str) : Determines which ports are the input and output 
            ports. 'Y' for input left, output right. 'Z' for input right and
            output left. 
                [Default] = 'Y'
            `microstep` (bool) : whether or not to operate in microstep mode
                [default] - False (factory default)
            `slope` (int) : slope setting
                [default] - 14 (factory default)
            `speed` (int) : initialization force or speed
                0 [default] - full plunger force and default speed
                1 - half plunger force and default speed
                2 - one third plunger force and default speed
                10-40 - full force and speed code X
                Refer to manual to pick right settings
                [default] = 16, 400Hz = 15 seconds per stroke.
            `debug` (bool) : turns on debug file, which logs extensive debug
                             output to 'XCalibur_debug.log' at
                             `debug_log_path`
                [default] - False
            `debug_log_path` : path to debug log file - only relevant if
                               `debug` == True.
                [default] - '' (cwd)

        """
        super(XCalibur, self).__init__(com_link)
        self.syringe_ul = syringe_ul
        self.direction = direction
        self.speed = speed
        self.min_speed = 0
        self.max_speed = 40
        self.state = {
            'plunger_pos': None,
            'port': None,
            'microstep': microstep,
            'start_speed': None,
            'top_speed': None,
            'cutoff_speed': None,
            'slope': slope
        }

        # Handle debug mode init
        self.debug = debug
        if self.debug:
            self.initDebugLogging(debug_log_path)

        self.setMicrostep(on=microstep)

        # Command chaining state information
        self.cmd_chain = ''
        self.exec_time = 0
        self.sim_speed_change = False
        self.sim_state = {k: v for k, v in self.state.items()}

        # Init functions
        self.updateSpeeds()
        self.getPlungerPos()
        self.getCurPort()
        self.updateSimState()

    #########################################################################
    # Debug functions                                                       #
    #########################################################################

    def initDebugLogging(self, debug_log_path):
        """ Initialize logger and log file handler """

        self.logger = logging.getLogger('XCalibur')
        fp = debug_log_path.rstrip('/') + '/XCalibur_debug.log'
        hdlr = logging.FileHandler(fp)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)

    def logCall(self, f_name, f_locals):
        """ Logs function params at call """

        if self.debug:
            self.logger.debug('-> {}: {}'.format(f_name, f_locals))

    def logDebug(self, msg):
        """ Handles debug logging if self.debug == True """

        if self.debug:
            self.logger.debug(msg)

    #########################################################################
    # Pump initialization                                                   #
    #########################################################################

    def init(self, speed=None, direction=None):
        """
        Initialize pump. Blocks until initialization is complete.
        `speed` (int) : initialization force or speed
                0 - full plunger force and default speed
                1 - half plunger force and default speed
                2 - one third plunger force and default speed
                10-40 - full force and speed code X
                Default = 16
        Speed codes: 0: 6000, 1: 5600, 2: 5000, 3: 4400, 4: 3800, 
            5: 3200, 6: 2600, 7: 2200, 8: 2000, 9: 1800, 10: 1600,
            11: 1400, 12: 1200, 13: 1000, 14: 800, 15: 600, 
            16: 400, 17: 200, 18: 190, 19: 180, 20: 170, 21: 160,
            22: 150, 23: 140, 24: 130, 25: 120, 26: 110, 27: 100,
            28: 90, 29: 80, 30: 70, 31: 60, 32: 50, 33: 40, 
            34: 30, 35: 20, 36: 18, 37: 16, 38: 14, 39: 12, 40: 10
            Speed codes encode the frequency at which the plunger
            moves (in Hz). See Tecan Cavro XCalibur manual for 
            information. 
            Indication: 6000Hz (speed code 0) = 1.25seconds per
            stroke. 10Hz (speed code 40) = 600seconds per stroke.
            Default to 16, 400Hz = 15 seconds per stroke.

        `direction` (str): Determines which ports are the input and output 
            ports. 'Y' for input left, output right. 'Z' for input right and
            output left. Default = Y
        

        """
        self.logCall('init', locals())

        speed = speed if speed is not None else self.speed
        direction = direction if direction is not None else self.direction

        cmd_string = '{0}{1}'.format(direction, speed)

        self.sendRcv(cmd_string, execute=True)
        self.waitReady()
        return 0  # 0 seconds left to wait

    #########################################################################
    # Command chain functions                                               #
    #########################################################################

    def executeChain(self, minimal_reset=False):
        """
        Executes and resets the current command chain (`self.cmd_chain`).
        Returns the estimated execution time (`self.exec_time`) for the chain.

        """
        self.logCall('executeChain', locals())

        # Compensate for reset time (tic/toc) prior to returning wait_time
        tic = time.time()
        self.sendRcv(self.cmd_chain, execute=True)
        exec_time = self.exec_time
        self.waitReady()
        self.resetChain(on_execute=True, minimal_reset=minimal_reset)
        toc = time.time()
        wait_time = exec_time - (toc-tic)
        if wait_time < 0:
            wait_time = 0
        return wait_time

    def resetChain(self, on_execute=False, minimal_reset=False):
        """
        Resets the command chain (`self.cmd_chain`) and execution time
        (`self.exec_time`). Optionally updates `slope` and `microstep`
        state variables, speeds, and simulation state.

        Kwargs:
            `on_execute` (bool) : should be used to indicate whether or not
                                  the chain being reset was executed, which
                                  will cue slope and microstep state
                                  updating (as well as speed updating).
            `minimal_reset` (bool) : minimizes additional polling of the
                                     syringe pump and updates state based
                                     on simulated calculations. Should
                                     be extremely reliable but use with
                                     caution.
        """
        self.logCall('resetChain', locals())

        self.cmd_chain = ''
        self.exec_time = 0
        if (on_execute and self.sim_speed_change):
            if minimal_reset:
                self.state = {k: v for k, v in self.sim_state.items()}
            else:
                self.state['slope'] = self.sim_state['slope']
                self.state['microstep'] = self.sim_state['microstep']
                self.updateSpeeds()
                self.getCurPort()
                self.getPlungerPos()
        self.sim_speed_change = False
        self.updateSimState()

    def updateSimState(self):
        """
        Copies the current state dictionary (`self.state`) to the
        simulation state dictionary (`self.sim_state`)

        """
        self.logCall('updateSimState', locals())

        self.sim_state = {k: v for k, v in self.state.items()}

    def cacheSimSpeeds(self):
        """
        Caches the simulation state speed settings when called. May
        be used for convenience functions in which speed settings
        need to be temporarily changed and then reverted

        """
        self.logCall('cacheSimSpeeds', locals())

        self._cached_start_speed = self.sim_state['start_speed']
        self._cached_top_speed = self.sim_state['top_speed']
        self._cached_cutoff_speed = self.sim_state['cutoff_speed']

    def restoreSimSpeeds(self):
        """ Restores simulation speeds cached by `self.cacheSimSpeeds` """
        self.logCall('restoreSimSpeeds', locals())

        self.sim_state['start_speed'] = self._cached_start_speed
        self.sim_state['top_speed'] = self._cached_top_speed
        self.sim_state['cutoff_speed'] = self._cached_cutoff_speed
        self.setTopSpeed(self._cached_top_speed)
        if 50 <= self._cached_start_speed <= 1000:
            self.setStartSpeed(self._cached_start_speed)
        if 50 <= self._cached_cutoff_speed <= 2700:
            self.setCutoffSpeed(self._cached_cutoff_speed)

    def execWrap(func, mode='safe'):
        """
        Decorator to wrap chainable commands, allowing for immediate execution
        of the wrapped command by passing in an `execute=True` kwarg.
        `mode`(str): If set to safe; perform "waitReady()" after every 
            execution to prevent Command Overflow errors.
            waitReady() input: timeout (seconds), polling_interval (seconds),
           delay (seconds).

        """
        @wraps(func)
        def addAndExec(self, *args, **kwargs):
            execute = False
            if 'execute' in kwargs:
                execute = kwargs.pop('execute')
            if 'minimal_reset' in kwargs:
                minimal_reset = kwargs.pop('minimal_reset')
            else:
                minimal_reset = False
            if 'timeout' in kwargs:
                timeout = kwars.pop('timeout')
            else:
                timeout = 60
            if 'polling_interval' in kwargs:
                polling_interval = kwargs.pop('polling_interval')
            else:
                polling_interval = 0.3
            if 'delay' in kwargs:
                delay = kwargs.pop('delay')
            else:
                delay = None
            
            #Execute function
            func(self, *args, **kwargs)

            if execute:
                return self.executeChain(minimal_reset=minimal_reset)
            #Waitready in safe mode
            if mode == 'safe':
                self.waitReady(timeout=timeout, 
                               polling_interval=polling_interval,
                               delay=delay)
        return addAndExec

    #########################################################################
    # Chainable high level functions                                        #
    #########################################################################

    @execWrap
    def extract(self, from_port, volume_ul):
        """ Extract `volume_ul` from `from_port` """
        self.logCall('extract', locals())

        steps = self._ulToSteps(volume_ul)
        self.changePort(from_port)
        self.movePlungerRel(steps)

    @execWrap
    def dispense(self, to_port, volume_ul):
        """ Dispense `volume_ul` from `to_port` """
        self.logCall('dispense', locals())

        steps = self._ulToSteps(volume_ul)
        self.changePort(to_port)
        self.movePlungerRel(-steps)

    #########################################################################
    # Chainable low level functions                                         #
    #########################################################################

    @execWrap
    def changePort(self, to_port):
        """
        Change port to `to_port`. If `from_port` is provided, the `direction`
        will be calculated to minimize travel time. `direction` may also be
        provided directly.

        Args:
            `to_port` (str) : Port to which to change, either 'input'
                or 'output'. Input and output ports are determined at 
                init() call with the direction variable.
                'CW' --> input is left port, output is right port.
                'CCW' --> input is right port, output is left port.

        """
        self.logCall('changePort', locals())

        if to_port.lower() != 'input' and to_port.lower() != 'output':
            raise(ValueError('`to_port` must be "input" or "output" not: {}'.format(to_port)))
        if to_port == 'input':
            cmd_string = 'I'
        if to_port == 'output':
            cmd_string = 'O'
        self.sim_state['port'] = to_port
        self.cmd_chain += cmd_string
        self.exec_time += 0.2

    @execWrap
    def movePlungerAbs(self, abs_position):
        """
        Moves the plunger to absolute position `abs_position`

        Args:
            `abs_position` (int) : absolute plunger position
                (0-24000) in microstep mode
                (0-3000) in standard mode

        """
        self.logCall('movePlungerAbs', locals())

        if self.sim_state['microstep']:
            if not 0 <= abs_position <= 24000:
                raise(ValueError('`abs_position` must be between 0 and 24000'
                                 ' when operating in microstep mode'
                                 ''.format(self.port_num)))
        else:
            if not 0 <= abs_position <= 3000:
                raise(ValueError('`abs_position` must be between 0 and 3000'
                                 ' when operating in standard mode'
                                 ''.format(self.port_num)))
        cmd_string = 'A{0}'.format(abs_position)
        cur_pos = self.sim_state['plunger_pos']
        delta_pos = cur_pos-abs_position
        self.sim_state['plunger_pos'] = abs_position
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(delta_pos))

    @execWrap
    def movePlungerRel(self, rel_position):
        """
        Moves the plunger to relative position `rel_position`. There is no
        front-end error handling -- invalid relative moves will result in
        error code 3 from the XCalibur, raising a `SyringeError`

        Args:
            `rel_position` (int) : relative plunger position
                if rel_position < 0 : plunger moves up (relative dispense)
                if rel_position > 0 : plunger moves down (relative extract)

        """
        self.logCall('movePlungerRel', locals())

        if rel_position < 0:
            cmd_string = 'D{0}'.format(abs(rel_position))
        else:
            cmd_string = 'P{0}'.format(rel_position)
        self.sim_state['plunger_pos'] += rel_position
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(rel_position))

    #########################################################################
    # Command set commands                                                  #
    #########################################################################

    @execWrap
    def setSpeed(self, speed_code):
        """ Set top speed by `speed_code` (see OEM docs) """
        self.logCall('setSpeed', locals())

        if not 0 <= speed_code <= 40:
            raise(ValueError('`speed_code` [{0}] must be between 0 and 40'
                             ''.format(speed_code)))
        self.speed = speed_code
        cmd_string = 'S{0}'.format(speed_code)
        self.sim_speed_change = True
        self._simIncToPulses(speed_code)
        self.cmd_chain += cmd_string

    @execWrap
    def setStartSpeed(self, pulses_per_sec):
        """ Set start speed in `pulses_per_sec` [50-1000] """
        self.logCall('setStartSpeed', locals())

        cmd_string = 'v{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setTopSpeed(self, pulses_per_sec):
        """ Set top speed in `pulses_per_sec` [5-6000] """
        self.logCall('setTopSpeed', locals())

        cmd_string = 'V{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setCutoffSpeed(self, pulses_per_sec):
        """ Set cutoff speed in `pulses_per_sec` [50-2700] """
        self.logCall('setCutoffSpeed', locals())

        cmd_string = 'c{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setSlope(self, slope_code, chain=False):
        self.logCall('setSlope', locals())

        if not 1 <= slope_code <= 20:
            raise(ValueError('`slope_code` [{0}] must be between 1 and 20'
                             ''.format(slope_code)))
        cmd_string = 'L{0}'.format(slope_code)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    # Chainable control commands
    @execWrap
    def repeatCmdSeq(self, num_repeats):
        self.logCall('repeatCmdSeq', locals())

        if not 0 < num_repeats < 30000:
            raise(ValueError('`num_repeats` [{0}] must be between 0 and 30000'
                             ''.format(num_repeats)))
        cmd_string = 'G{0}'.format(num_repeats)
        self.cmd_chain += cmd_string
        self.exec_time *= num_repeats

    @execWrap
    def markRepeatStart(self):
        self.logCall('markRepeatStart', locals())

        cmd_string = 'g'
        self.cmd_chain += cmd_string

    @execWrap
    def delayExec(self, delay_ms):
        """ Delays command execution for `delay` milliseconds """
        self.logCall('delayExec', locals())

        if not 0 < delay_ms < 30000:
            raise(ValueError('`delay` [{0}] must be between 0 and 40000 ms'
                             ''.format(delay_ms)))
        cmd_string = 'M{0}'.format(delay_ms)
        self.cmd_chain += cmd_string

    @execWrap
    def haltExec(self, input_pin=0):
        """
        Used within a command string to halt execution until another [R]
        command is sent, or until TTL pin `input_pin` goes low

        Kwargs:
            `input_pin` (int) : input pin code corresponding to the desired
                                TTL input signal pin on the XCalibur
                0 - either 1 or 2
                1 - input 1 (J4 pin 7)
                2 - input 2 (J4 pin 8)

        """
        self.logCall('haltExec', locals())

        if not 0 <= input_pin < 2:
            raise(ValueError('`input_pin` [{0}] must be between 0 and 2'
                             ''.format(input_sig)))
        cmd_string = 'H{0}'.format(input_sig)
        return self.sendRcv(cmd_string)

    #########################################################################
    # Report commands (cannot be chained)                                   #
    #########################################################################

    def updateSpeeds(self):
        self.logCall('updateSpeeds', locals())

        self.getStartSpeed()
        self.getTopSpeed()
        self.getCutoffSpeed()

    def getSpeed(self):
        """ Returns the saved speed code """
        return self.speed

    def getPlungerPos(self):
        """ Returns the absolute plunger position as an int (0-3000) """
        self.logCall('getPlungerPos', locals())

        cmd_string = '?'
        data = self.sendRcv(cmd_string)
        self.state['plunger_pos'] = int(data)
        return self.state['plunger_pos']

    def getStartSpeed(self):
        """ Returns the start speed as an int (in pulses/sec) """
        self.logCall('getStartSpeed', locals())

        cmd_string = '?1'
        data = self.sendRcv(cmd_string)
        self.state['start_speed'] = int(data)
        return self.state['start_speed']

    def getTopSpeed(self):
        """ Returns the top speed as an int (in pulses/sec) """
        self.logCall('getTopSpeed', locals())

        cmd_string = '?2'
        data = self.sendRcv(cmd_string)
        self.state['top_speed'] = int(data)
        return self.state['top_speed']

    def getCutoffSpeed(self):
        """ Returns the cutoff speed as an int (in pulses/sec) """
        self.logCall('getCutoffSpeed', locals())

        cmd_string = '?3'
        data = self.sendRcv(cmd_string)
        self.state['cutoff_speed'] = int(data)
        return self.state['cutoff_speed']

    def getEncoderPos(self):
        """ Returns the current encoder count on the plunger axis """
        self.logCall('getEncoderPos', locals())

        cmd_string = '?4'
        data = self.sendRcv(cmd_string)
        return int(data)

    def getCurPort(self):
        """ 
        Returns the current port position 'i' for input 
        'o' for output.
        
        """
        self.logCall('getCurPort', locals())

        cmd_string = '?6'
        data = self.sendRcv(cmd_string)
        with self._syringeErrorHandler():
            try:
                port = data.decode('utf-8')
            except ValueError:
                raise SyringeError(7, self.__class__.ERROR_DICT)
            self.state['port'] = port
            return port

    def getBufferStatus(self):
        """ Returns the current cmd buffer status (0=empty, 1=non-empty) """
        self.logCall('getBufferStatus', locals())

        cmd_string = '?10'
        data = self.sendRcv(cmd_string)
        return int(data)

    #########################################################################
    # Config commands                                                       #
    #########################################################################

    def setMicrostep(self, on=False):
        """ Turns microstep mode on or off """
        self.logCall('setMicrostep', locals())

        cmd_string = 'N{0}'.format(int(on))
        self.sendRcv(cmd_string, execute=True)
        self.microstep = on

    #########################################################################
    # Control commands                                                      #
    #########################################################################

    def terminateCmd(self):
        self.logCall('terminateCommand', locals())

        cmd_string = 'T'
        return self.sendRcv(cmd_string, execute=True)

    #########################################################################
    # Communication handlers and special functions                          #
    #########################################################################

    @contextmanager
    def _syringeErrorHandler(self):
        """
        Context manager to handle `SyringeError` based on error code. Right
        now this just handles error codes 7, 9, and 10 by initializing the
        pump and then re-running the previous command.

        """
        try:
            yield
        except SyringeError as e:
            self.logDebug('ErrorHandler: caught error code {}'.format(
                          e.err_code))
            if e.err_code in [7, 9, 10]:
                last_cmd = self.last_cmd
                self.resetChain()
                try:
                    self.logDebug('ErrorHandler: attempting re-init')
                    self.init()
                except SyringeError as e:
                    self.logDebug('ErrorHandler: Error during re-init '
                                  '[{}]'.format(e.err_code))
                    if e.err_code in [7, 9, 10]:
                        pass
                    else:
                        raise e
                self._waitReady()
                self.logDebug('ErrorHandler: resending last command {} '
                              ''.format(last_cmd))
                self.sendRcv(last_cmd)
            else:
                self.logDebug('ErrorHandler: error not in [7, 9, 10], '
                              're-raising [{}]'.format(e.err_code))
                self.resetChain()
                raise e
        except Exception as e:
            self.resetChain()
            raise e

    def waitReady(self, timeout=10, polling_interval=0.3, delay=None):
        """
        Waits a maximum of `timeout` seconds for the syringe to be
        ready to accept another set command, polling every `polling_interval`
        seconds. If a `delay` is provided, the function will sleep `delay`
        seconds prior to beginning polling.

        """
        self.logCall('waitReady', locals())
        with self._syringeErrorHandler():
            self._waitReady(timeout=timeout, polling_interval=polling_interval,
                            delay=delay)

    def sendRcv(self, cmd_string, execute=False):
        """
        Send a raw command string and return a tuple containing the parsed
        response data: (Data, Ready). If the syringe is ready to accept
        another command, `Ready` with be 'True'.

        Args:
            `cmd_string` (bytestring) : a valid Tecan XCalibur command string
        Kwargs:
            `execute` : if 'True', the execute byte ('R') is appended to the
                        `cmd_string` prior to sending
        Returns:
            `parsed_reponse` (tuple) : parsed pump response tuple

        """
        self.logCall('sendRcv', locals())

        if execute:
            cmd_string += 'R'
        self.last_cmd = cmd_string
        self.logDebug('sendRcv: sending cmd_string: {}'.format(cmd_string))
        with self._syringeErrorHandler():
            parsed_response = super(XCalibur, self)._sendRcv(cmd_string)
            self.logDebug('sendRcv: received response: {}'.format(
                          parsed_response))
            data = parsed_response[0]
            return data

    def _calcPlungerMoveTime(self, move_steps):
        """
        Calculates plunger move time using equations provided by Tecan.
        Assumes that all input values have been validated

        """
        sd = self.sim_state
        start_speed = sd['start_speed']
        top_speed = sd['top_speed']
        cutoff_speed = sd['cutoff_speed']
        slope = sd['slope']
        microstep = sd['microstep']

        slope *= 2500.0
        if microstep:
            move_steps = move_steps / 8.0
        theo_top_speed = sqrt((4.0 * move_steps*slope) + start_speed ** 2.0)
        # If theoretical top speed will not exceed cutoff speed
        if theo_top_speed < cutoff_speed:
            move_t = theo_top_speed - (start_speed/slope)
        else:
            theo_top_speed = sqrt(((2.0*move_steps*slope) +
                                  ((start_speed**2.0+cutoff_speed**2.0)/2.0)))
        # If theoretical top speed with exceed cutoff speed but not
        # reach the set top speed
        if cutoff_speed < theo_top_speed < top_speed:
            move_t = ((1 / slope) * (2.0 * theo_top_speed - start_speed -
                                     cutoff_speed))
        # If start speed, top speed, and cutoff speed are all the same
        elif start_speed == top_speed == cutoff_speed:
            move_t = (2.0 * move_steps) / top_speed
        # Otherwise, calculate time spent in each phase (start, constant,
        # ramp down)
        else:
            ramp_up_halfsteps = ((top_speed ** 2.0 - start_speed ** 2.0) /
                                (2.0 * slope))
            ramp_down_halfsteps = ((top_speed ** 2.0 - cutoff_speed ** 2.0) /
                                  (2.0 * slope))
            if (ramp_up_halfsteps + ramp_down_halfsteps) < (2.0 * top_speed):
                ramp_up_t = (top_speed - start_speed) / slope
                ramp_down_t = (top_speed - cutoff_speed) / slope
                constant_halfsteps = (2.0 * move_steps - ramp_up_halfsteps -
                                      ramp_down_halfsteps)
                constant_t = constant_halfsteps / top_speed
                move_t = ramp_up_t + ramp_down_t + constant_t
        return move_t

    def _ulToSteps(self, volume_ul, microstep=None):
        """
        Converts a volume in microliters (ul) to encoder steps.
        Rounds down to nearest integer.

        Args:
            `volume_ul` (int) : volume in microliters
        Kwargs:
            `microstep` (bool) : whether to convert to standard steps or
                                 microsteps

        """
        if microstep is None:
            microstep = self.state['microstep']
        if microstep:
            steps = volume_ul * (24000/self.syringe_ul)
        else:
            steps = volume_ul * (3000/self.syringe_ul)
        return int(steps)

    def _simIncToPulses(self, speed_inc):
        """
        Updates simulation speeds given a speed increment setting (`speed_inc`)
        following XCalibur handling of speed changes (i.e. cutoff speed cannot
        be higher than top speed, so it is automatically adjusted on the pump)

        """
        top_speed = self.__class__.SPEED_CODES[speed_inc]
        self.sim_state['top_speed'] = top_speed
        if self.sim_state['start_speed'] > top_speed:
            self.sim_state['start_speed'] = top_speed
        if self.sim_state['cutoff_speed'] > top_speed:
            self.sim_state['cutoff_speed'] = top_speed


#############################################################################
#############################################################################
##                                                                         ##
##                        Tecan XE100 Syringe Pump                         ##
##                                                                         ##
#############################################################################
#############################################################################

class XE1000(Syringe):
    """
    Class to control Tecan XE1000 pumps.
    """

    def __init__(self, com_link, syringe_ul=2500, speed=400,
                        debug=False, debug_log_path='.'):
        """
        Object initialization function.

        Args:
            `com_link` (Object) : instantiated TecanAPI subclass / transport
                                  layer (see transport.py)
                *Must have a `.sendRcv(cmd)` instance method to send a command
                    string and parse the reponse (see transport.py)
        Kwargs:
            `syringe_ul` (int) : syringe volume in microliters
                [default] - 2500
            `speed` (int) : syringe plunger speed, 20-600, [default] = 400
                            speed / 10 = time in sec for full plunger move 
            `debug` (bool) : turns on debug file, which logs extensive debug
                             output to 'XCalibur_debug.log' at
                             `debug_log_path`
                [default] - False
            `debug_log_path` : path to debug log file - only relevant if
                               `debug` == True.
                [default] - '' (cwd)

        """
        super(XE1000, self).__init__(com_link)
        self.syringe_ul = syringe_ul
        self.speed = speed
        self.min_speed = 20
        self.max_speed = 600
        self.reInitiated = 0
        self.state = {
            'plunger_pos': None,
            'cur_port': None,
            'speed': None,
            'in_port' : None,
            'backlash_steps': 15 #default, setBacklashSteps() to change
        }

        # Handle debug mode init
        self.debug = debug
        if self.debug:
            self.initDebugLogging(debug_log_path)

        # Command chaining state information
        self.cmd_chain = ''
        self.exec_time = 0
        self.sim_speed_change = False
        self.sim_state = {k: v for k, v in self.state.items()}

        # Init functions
        self.updateState()
        self.updateSimState()

    #########################################################################
    # Debug functions                                                       #
    #########################################################################

    def initDebugLogging(self, debug_log_path):
        """ Initialize logger and log file handler """

        self.logger = logging.getLogger('XE1000')
        fp = debug_log_path.rstrip('/') + '/XE1000_debug.log'
        hdlr = logging.FileHandler(fp)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)

    def logCall(self, f_name, f_locals):
        """ Logs function params at call """

        if self.debug:
            self.logger.debug('-> {}: {}'.format(f_name, f_locals))

    def logDebug(self, msg):
        """ Handles debug logging if self.debug == True """

        if self.debug:
            self.logger.debug(msg)

    #########################################################################
    # Pump initialization                                                   #
    #########################################################################

    def init(self, in_port = 'left', init_speed = 20):
        """
        Initialize pump.
        in_port: 'left' or 'right'
        init_speed determines the seconds/stroke of the initiazion cycle, 
        range 2-20. Blocks until initialization is complete.

        """
        self.logCall('init', locals())

        self.state['in_port'] = in_port
        if in_port == 'left':
            init_command = 'Z'
        if in_port == 'right':
            init_command = 'Y'
        cmd_string = '{0}{1}'.format(
                     init_command,
                     init_speed)
        self.sendRcv(cmd_string, execute=True)
        self.waitReady()
        self.setSpeed(speed=self.speed, execute=True)
        self.waitReady()
        return 0  # 0 seconds left to wait

    #########################################################################
    # Command chain functions                                               #
    #########################################################################

    def executeChain(self, minimal_reset=False):
        """
        Executes and resets the current command chain (`self.cmd_chain`).
        Returns the estimated execution time (`self.exec_time`) for the chain.

        """
        self.logCall('executeChain', locals())

        # Compensaate for reset time (tic/toc) prior to returning wait_time
        tic = time.time()
        self.sendRcv(self.cmd_chain, execute=True)
                #LEBorm added a waitReady() and removed exec_time
        #Otherwise the program was sending commands too quick.

        #exec_time = self.exec_time #Removed by LEBorm
        self.waitReady()
        self.resetChain(on_execute=True, minimal_reset=minimal_reset)
        toc = time.time()
        #wait_time = exec_time - (toc-tic) #Removed by LEBorm
        wait_time = toc - tic
        if wait_time < 0:
            wait_time = 0
        return wait_time

    def resetChain(self, on_execute=False, minimal_reset=False):
        """
        Resets the command chain (`self.cmd_chain`) and execution time
        (`self.exec_time`). Optionally updates speeds, and simulation state.

        Kwargs:
            `on_execute` (bool) : should be used to indicate whether or not
                                  the chain being reset was executed, which
                                  will speed updating.
            `minimal_reset` (bool) : minimizes additional polling of the
                                     syringe pump and updates state based
                                     on simulated calculations. Should
                                     be extremely reliable but use with
                                     caution.
        """
        self.logCall('resetChain', locals())

        self.cmd_chain = ''
        self.exec_time = 0
        if (on_execute and self.sim_speed_change):
            if minimal_reset:
                self.state = {k: v for k, v in self.sim_state.items()}
            else:
                self.updateState()
        self.sim_speed_change = False
        self.updateSimState()

    def updateSimState(self):
        """
        Copies the current state dictionary (`self.state`) to the
        simulation state dictionary (`self.sim_state`)

        """
        self.logCall('updateSimState', locals())

        self.sim_state = {k: v for k, v in self.state.items()}

    def cacheSimSpeeds(self):
        """
        Caches the simulation state speed setting when called. May
        be used for convenience functions in which speed settings
        need to be temporarily changed and then reverted

        """
        self.logCall('cacheSimSpeed', locals())

        self._cached_speed = self.sim_state['speed']


    def restoreSimSpeeds(self):
        """ Restores simulation speed cached by `self.cacheSimSpeeds` """
        self.logCall('restoreSimSpeeds', locals())

        self.sim_state['speed'] = self._cached_speed
        if 20 <= self._cached_speed <= 600:
            self.setSpeed(self._cached_speed)

    def execWrap(func):
        """
        Decorator to wrap chainable commands, allowing for immediate execution
        of the wrapped command by passing in an `execute=True` kwarg.

        """
        @wraps(func)
        def addAndExec(self, *args, **kwargs):
            name = 'XE1000 ' + str(func).split(' ')[1] + ' : '
            execute = False
            if 'execute' in kwargs:
                execute = kwargs.pop('execute')
            if 'minimal_reset' in kwargs:
                minimal_reset = kwargs.pop('minimal_reset')
            else:
                minimal_reset = False
            func(self, *args, **kwargs)
            if execute:
                #Executes the chain, waits untill ready and updates state params
                return name, self.executeChain(minimal_reset=minimal_reset),
                self.updateState()
                #self.waitReady(), self.updateState()                
        return addAndExec

    #########################################################################
    # Chainable high level functions                                        #
    #########################################################################

    @execWrap
    def extract(self, from_port, volume_ul):
        """
        Extract `volume_ul` from `from_port`
        from_port: 1 or `input` or 2 or `output`

        """
        self.logCall('extract', locals())

        steps = self._ulToSteps(volume_ul)
        if from_port.lower() != 'input' and from_port != 1 and from_port.lower() != 'output' and from_port != 2:
            raise(ValueError('`from_port` must be 1 or "input" or 2 or "output", not: {}'.format(from_port)))

        elif from_port.lower() == 'input' or from_port == 1:
            self.changePort('input')
            self.waitReady()

        elif from_port.lower == 'output' or from_port == 2:
            self.changePort('output')
            self.waitReady()

        self.movePlungerRel(steps)

    @execWrap
    def dispense(self, to_port, volume_ul):
        """
        Dispense `volume_ul` to `to_port`
        from_port: 1 or `input` or 2 or `output`

        """
        self.logCall('dispense', locals())

        steps = self._ulToSteps(volume_ul)
        if to_port.lower() != 'input' and to_port != 1 and to_port.lower() != 'output' and to_port != 2:
            raise(ValueError('`to_port` must be 1 or "input" or 2 or "output", not: {}'.format(to_port)))
        elif to_port == 'input':
            self.changePort('input')
            self.waitReady()
        elif to_port == 'output':
            self.changePort('output')
            self.waitReady()
        self.movePlungerRel(-steps)


    #########################################################################
    # Chainable low level functions                                         #
    #########################################################################

    @execWrap
    def changePort(self, to_port, *kwargs):
        """
        Change port to provided port.
        Input:
        `to_port`(int or str): Port to move to, either  1 or 'input' or 2 or 
        'output' which are defined during the call of the init() function.
        1 equals 'input', 2 equals 'output'

        Kwargs are ignored. Added to make different pump models compatible 
        with the same code.

        """
        if to_port.lower() != 'input' and to_port != 1 and to_port.lower() != 'output' and to_port != 2:
            raise(ValueError('`to_port` must be 1 or "input" or 2 or "output", not: {}'.format(to_port)))

        if to_port.lower() == 'input' or to_port == 1:
            cmd_string = 'I'
            self.state['cur_port'] = 'input'
            self.cmd_chain += cmd_string

        elif to_port.lower() == 'output' or to_port == 2:
            cmd_string = 'O'
            self.state['cur_port'] = 'output'
            self.cmd_chain += cmd_string

    @execWrap
    def changePortInput(self):
        """
        Change port to input port. (defined by init())

        """
        cmd_string = 'I'
        self.state['cur_port'] = 'input'
        self.cmd_chain += cmd_string

    @execWrap
    def changePortOutput(self):
        """
        Change port to Output port. (defined by init())

        """
        cmd_string = 'O'
        self.state['cur_port'] = 'output'
        self.cmd_chain += cmd_string

    @execWrap
    def changePortBypass(self):
        """
        Change port to Bypass port.

        """
        cmd_string = 'B'
        self.state['cur_port'] = 'bypass'
        self.cmd_chain += cmd_string

    @execWrap
    def movePlungerAbs(self, abs_position):
        """
        Moves the plunger to absolute position `abs_position`

        Args:
            `abs_position` (int) : absolute plunger position
                                   range: 0 - 1000

        """
        self.logCall('movePlungerAbs', locals())

        if not 0 <= abs_position <= 1000:
            raise(ValueError('`abs_position` must be between 0 and 1000'))

        cmd_string = 'A{0}'.format(abs_position)
        cur_pos = self.sim_state['plunger_pos']
        delta_pos = cur_pos-abs_position
        self.sim_state['plunger_pos'] = abs_position
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(delta_pos))
  

    @execWrap
    def movePlungerRel(self, rel_position):
        """
        Moves the plunger to relative position `rel_position`. There is no
        front-end error handling -- invalid relative moves will result in
        error code 3 from the XCalibur, raising a `SyringeError`

        Args:
            `rel_position` (int) : relative plunger position
                if rel_position < 0 : plunger moves up (relative dispense)
                if rel_position > 0 : plunger moves down (relative extract)

        """
        self.logCall('movePlungerRel', locals())

        if rel_position < 0:
            cmd_string = 'D{0}'.format(abs(rel_position))
        else:
            cmd_string = 'P{0}'.format(rel_position)
        self.sim_state['plunger_pos'] += rel_position
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(rel_position))
        self.state['plunger_pos'] = self.getPlungerPos()


    #########################################################################
    # Convenience functions                                                 #
    #########################################################################

    @execWrap
    def primePort(self, cycles=1):
        """
        Prime the pump. It will perform two complete aspiration/dispense
        cycles of the full syringe volume.
        Extracting from the input port and dispensing to the output port,
        as set during init()
        `cycles` = number of full aspiration/dispense cycles. max = 2

        """
        self.logCall('setSpeed', locals())
        if not 0 < cycles < 3:
            raise(ValueError('`cycles` should be 1 or 2'))
        #For some unknown reason the 'P' command (P for prime) does not work
        #According to the manual 'A0IA1000OA0' is the same as one cycle of 'P'
        cmd = 'A0IA1000OA0'
        cmd_string = cmd * cycles
        self.cmd_chain += cmd_string

    #########################################################################
    # Command set commands                                                  #
    #########################################################################

    @execWrap
    def setSpeed(self, speed):
        """ Set speed 
        `speed` (int) : syringe plunger speed, 20-600
                        speed / 10 = time in sec for full plunger move 
        
        """
        self.logCall('setSpeed', locals())

        if not self.min_speed <= speed <= self.max_speed:
            raise(ValueError('`speed` [{}] must be between {} and {}'
                             ''.format(speed, self.min_speed, self.max_speed)))
        cmd_string = 'S{0}'.format(speed)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

#LBorm: test this

    @execWrap
    def setBacklashSteps(self, steps):
        """ Set backlash steps (compensate for mechanical play) 
        `steps` (int) : steps in range 0 to 20, default = 15
        
        """
        self.logCall('setBacklashSteps', locals())

        if not 0 <= steps <= 20:
            raise(ValueError('`steps` [{0}] must be between 0 and 20'
                             ''.format(steps)))
        cmd_string = 'K{}'.format(steps)
        self.cmd_chain += cmd_string


    # Chainable control commands

    @execWrap
    def repeatCmdSeq(self, num_repeats):
        self.logCall('repeatCmdSeq', locals())

        if not 0 < num_repeats < 30000:
            raise(ValueError('`num_repeats` [{0}] must be between 0 and 30000'
                             ''.format(num_repeats)))
        cmd_string = 'G{0}'.format(num_repeats)
        self.cmd_chain += cmd_string
        self.exec_time *= num_repeats

    @execWrap
    def markRepeatStart(self):
        self.logCall('markRepeatStart', locals())

        cmd_string = 'g'
        self.cmd_chain += cmd_string

    @execWrap
    def delayExec(self, delay_ms):
        """ Delays command execution for `delay` milliseconds """
        self.logCall('delayExec', locals())

        if not 0 < delay_ms < 30000:
    #changed 40000 in the error message to 30000. I think it was a mistake
            raise(ValueError('`delay` [{0}] must be between 0 and 30000 ms'
                             ''.format(delay_ms)))
        cmd_string = 'M{0}'.format(delay_ms)
        self.cmd_chain += cmd_string

    @execWrap
    def haltExec(self, input_pin=0):
        """
        Used within a command string to halt execution until another [R]
        command is sent, or until TTL pin `input_pin` goes low

        Kwargs:
            `input_pin` (int) : input pin code corresponding to the desired
                                TTL input signal pin on the XCalibur
                0 - either 1 or 2
                1 - input 1 (J4 pin 7)
                2 - input 2 (J4 pin 8)

        """
        self.logCall('haltExec', locals())

        if not 0 <= input_pin < 2:
            raise(ValueError('`input_pin` [{0}] must be between 0 and 2'
                             ''.format(input_sig)))
        cmd_string = 'H{0}'.format(input_sig)
        return self.sendRcv(cmd_string)

    #########################################################################
    # Report commands (cannot be chained)                                   #
    #########################################################################

    def updateState(self):
        """ Update speed, plunger position and sim state"""
        self.logCall('updateSpeeds', locals())

        self.getSpeed()
        self.getPlungerPos()
        self.getBacklashSteps()
        self.updateSimState()

    def getSpeed(self):
        """ Returns the speed as an int (20-600) """
        self.logCall('getSpeed', locals())
        
        cmd_string = '?S'
        data = self.sendRcv(cmd_string)
        time.sleep(0.5)
        self.state['speed'] = int(data)
        return self.state['speed']

    def getPlungerPos(self):
        """ Returns the absolute plunger position as an int (0-3000) """
        self.logCall('getPlungerPos', locals())

        cmd_string = '?'
        data = self.sendRcv(cmd_string)
        time.sleep(0.5)
        self.state['plunger_pos'] = int(data)
        return self.state['plunger_pos']

    def getBufferStatus(self):
        """ Returns the current cmd buffer status (0=empty, 1=non-empty) """
        self.logCall('getBufferStatus', locals())

        cmd_string = 'F'
        data = self.sendRcv(cmd_string)
        time.sleep(0.5)
        return int(data)

    def getBacklashSteps(self):
        """ Returns the number of backlash steps, int 0-20 """
        self.logCall('getBacklashSteps', locals())

        cmd_string = '?K'
        data = self.sendRcv(cmd_string)
        time.sleep(0.5)
        self.state['backlash_steps'] = int(data)
        return self.state['backlash_steps']

    #########################################################################
    # Control commands                                                      #
    #########################################################################

    def terminateCmd(self):
        self.logCall('terminateCommand', locals())

        cmd_string = 'T'
        return self.sendRcv(cmd_string, execute=True)

    #########################################################################
    # Communication handlers and special functions                          #
    #########################################################################

    @contextmanager
    def _syringeErrorHandler(self):
        """
        Context manager to handle `SyringeError` based on error code. Right
        now this just handles error codes 7, 9, and 10 by initializing the
        pump and then re-running the previous command.

        """
        try:
            yield
        except SyringeError as e:
            self.logDebug('ErrorHandler: caught error code {}'.format(
                          e.err_code))
            if e.err_code in [7, 9, 10]:
                last_cmd = self.last_cmd
                self.resetChain()
                try:
                    self.logDebug('ErrorHandler: attempting re-init')
#LEBorm: Test if this works
                    print('re-initiating after syringe error. Adjust the speed to prevent this')
                    self.init(in_port = self.state['in_port'])
                    self.setSpeed(self.state['speed'])
                    self.reInitiated += 1
                    print('re-initiated after syringe error for the {} time'
                            .format(self.reInitiated))
                except SyringeError as e:
                    self.logDebug('ErrorHandler: Error during re-init '
                                  '[{}]'.format(e.err_code))
                    if e.err_code in [7, 9, 10]:
                        pass
                    else:
                        raise e
                self._waitReady()
                self.logDebug('ErrorHandler: resending last command {} '
                              ''.format(last_cmd))
                self.sendRcv(last_cmd)
            else:
                self.logDebug('ErrorHandler: error not in [7, 9, 10], '
                              're-raising [{}]'.format(e.err_code))
                self.resetChain()
                raise e
        except Exception as e:
            self.resetChain()
            raise e

    def waitReady(self, timeout=10, polling_interval=0.3, delay=None):
        """
        Waits a maximum of `timeout` seconds for the syringe to be
        ready to accept another set command, polling every `polling_interval`
        seconds. If a `delay` is provided, the function will sleep `delay`
        seconds prior to beginning polling.

        """
        self.logCall('waitReady', locals())
        with self._syringeErrorHandler():
            self._waitReady(timeout=timeout, polling_interval=polling_interval,
                            delay=delay)

    def sendRcv(self, cmd_string, execute=False):
        """
        Send a raw command string and return a tuple containing the parsed
        response data: (Data, Ready). If the syringe is ready to accept
        another command, `Ready` with be 'True'.

        Args:
            `cmd_string` (bytestring) : a valid Tecan XCalibur command string
        Kwargs:
            `execute` : if 'True', the execute byte ('R') is appended to the
                        `cmd_string` prior to sending
        Returns:
            `parsed_reponse` (tuple) : parsed pump response tuple

        """
        self.logCall('sendRcv', locals())

        if execute:
            cmd_string += 'R'
        self.last_cmd = cmd_string
        self.logDebug('sendRcv: sending cmd_string: {}'.format(cmd_string))
        with self._syringeErrorHandler():
            parsed_response = super(XE1000, self)._sendRcv(cmd_string)
            self.logDebug('sendRcv: received response: {}'.format(
                          parsed_response))
            data = parsed_response[0]
            return data

    def _calcPlungerMoveTime(self, move_steps):
        """
        Calculates plunger move time in seconds.
        Assumes that all input values have been validated

        """
        move_t = ((move_steps / 1000.) * self.speed)/10
        return move_t

    def _ulToSteps(self, volume_ul):
        """
        Converts a volume in microliters (ul) to encoder steps.
        Rounds down to nearest integer.

        Args:
            `volume_ul` (int) : volume in microliters

        """
        if not 0 < volume_ul <= self.syringe_ul:
            raise(ValueError('Volume too large for syringe with volume: {}'
            .format(self.syringe_ul))) 
        steps = int(volume_ul * (1000./self.syringe_ul))
        return steps
