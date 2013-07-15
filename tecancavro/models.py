"""
models.py

Contains Tecan Cavro model-specific classes that inherit from the `Syringe`
class in syringe.py.

"""
import time

from math import sqrt
from time import sleep
from functools import wraps
from contextlib import contextmanager

from syringe import Syringe, SyringeError, SyringeTimeout


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
                 microstep=False, waste_port=9, slope=14, init_force=0):
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

        """
        super(XCaliburD, self).__init__(com_link)
        self.num_ports = num_ports
        self.syringe_ul = syringe_ul
        self.direction = direction
        self.waste_port = waste_port
        self.init_force = init_force
        self.state = {
            'port': None,
            'microstep': microstep,
            'start_speed': None,
            'top_speed': None,
            'cutoff_speed': None,
            'slope': slope
        }
        self.setMicrostep(on=microstep)

        # Command chaining state information
        self.cmd_chain = ''
        self.exec_time = 0
        self.sim_speed_change = False
        self.sim_state = {k: v for k,v in self.state.iteritems()}

        # Init functions
        self.updateSpeeds()
        self.getCurPort()
        self.updateSimState()


    def init(self, init_force=None, direction=None, in_port=0,
             out_port=0):
        """
        Initialize pump. Uses instance `self.init_force` and `self.direction`
        if not provided
        """
        if not init_force: init_force = self.init_force
        if not direction: direction = self.direction
        if self.waste_port and out_port == 0:
            out_port = self.waste_port
        cmd_string = '{0}{1},{2},{3}'.format(
                     self.__class__.DIR_DICT[direction][1],
                     init_force, in_port, out_port)
        self.sendRcv(cmd_string, execute=True)
        self.waitReady()
        return 0  # 0 seconds left to wait

    # Convenience functions

    def extractToWaste(self, in_port, volume_ul, out_port=None):
        """
        Extracts `volume_ul` from `in_port`. If the relative plunger move
        exceeds the encoder range, the syringe will dispense to `out_port`,
        which defaults to `self.waste_port`.
        """
        if not out_port: out_port = self.waste_port
        steps = self._ulToSteps(volume_ul)
        self.changePort(in_port)
        self.waitReady()
        try:
            return self.movePlungerRel(steps, execute=True)
        except SyringeError, e:
            # Clear the previous commands from the command chain
            self.resetChain()
            self.waitReady()
            self.changePort(out_port, from_port=in_port)
            self.cacheSimSpeeds()
            self.setSpeed(0)
            self.movePlungerAbs(0)
            self.changePort(in_port, from_port=out_port)
            self.restoreSimSpeeds()
            self.movePlungerRel(steps)
            self.changePort(out_port, from_port=in_port)
            return self.executeChain()

    # Chain functions

    def executeChain(self):
        """
        Executes and resets the current command chain (`self.cmd_chain`).
        Returns the estimated execution time (`self.exec_time`) for the chain.

        """
        tic = time.time()
        self.sendRcv(self.cmd_chain, execute=True)
        exec_time = self.exec_time
        self.resetChain(on_execute=True)
        toc = time.time()
        wait_time = exec_time - (toc-tic)
        if wait_time < 0:
            wait_time = 0
        return wait_time

    def resetChain(self, on_execute=False):
        """
        Resets the command chain (`self.cmd_chain`) and execution time
        (`self.exec_time`). Optionally updates `slope` and `microstep`
        state variables, speeds, and simulation state.

        Kwargs:
            `on_execute` (bool) : should be used to indicate whether or not
                                  the chain being reset was executed, which
                                  will cue slope and microstep state
                                  updating (as well as speed updating).
        """
        self.cmd_chain = ''
        self.exec_time = 0
        if (on_execute and self.sim_speed_change):
            self.state['slope'] = self.sim_state['slope']
            self.state['microstep'] = self.sim_state['microstep']
            self.updateSpeeds()
            self.getCurPort()
        self.sim_speed_change = False
        self.updateSimState()

    def updateSimState(self):
        """
        Copies the current state dictionary (`self.state`) to the
        simulation state dictionary (`self.sim_state`)

        """
        self.sim_state = {k: v for k,v in self.state.iteritems()}

    def cacheSimSpeeds(self):
        """
        Caches the simulation state speed settings when called. May
        be used for convenience functions in which speed settings
        need to be temporarily changed and then reverted

        """
        self._cached_start_speed = self.sim_state['start_speed']
        self._cached_top_speed = self.sim_state['top_speed']
        self._cached_cutoff_speed = self.sim_state['cutoff_speed']

    def restoreSimSpeeds(self):
        """ Restores simulation speeds cached by `self.cacheSimSpeeds` """
        self.sim_state['start_speed'] = self._cached_start_speed
        self.sim_state['top_speed'] = self._cached_top_speed
        self.sim_state['cutoff_speed'] = self._cached_cutoff_speed
        self.setTopSpeed(self._cached_top_speed)
        self.setCutoffSpeed(self._cached_cutoff_speed)
        self.setStartSpeed(self._cached_start_speed)

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
            func(self, *args, **kwargs)
            if execute:
                return self.executeChain()
        return addAndExec

    # Chainable convenience functions

    @execWrap
    def extract(self, from_port, volume_ul):
        """ Extract `volume_ul` from `from_port` """
        steps = self._ulToSteps(volume_ul)
        self.changePort(from_port)
        self.movePlungerRel(steps)

    @execWrap
    def dispense(self, to_port, volume_ul):
        """ Dispense `volume_ul` from `to_port` """
        steps = self._ulToSteps(volume_ul)
        self.changePort(to_port)
        self.movePlungerRel(-steps)

    # Chainable low-level functions

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
        if not 0 < to_port <= self.num_ports:
            raise(ValueError('`in_port` [{0}] must be between 1 and '
                             '`num_ports` [{1}]'.format(to_port,
                             self.num_ports)))
        if not from_port: from_port = self.sim_state['port']
        diff = to_port - from_port
        if abs(diff) >= 7: diff = -diff
        if diff < 0: direction = 'CCW'
        else: direction = 'CW'
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
        if self.sim_state['microstep']:
            if not 0 <= abs_position <= 24000:
                raise(ValueError('`abs_position` must be between 0 and 40000'
                                 ' when operating in microstep mode'.format(
                                 self.port_num)))
        else:
            if not 0 <= abs_position <= 3000:
                raise(ValueError('`abs_position` must be between 0 and 40000'
                                 ' when operating in microstep mode'.format(
                                 self.port_num)))
        cmd_string = 'A{0}'.format(abs_position)
        cur_pos = self.getPlungerPos()
        delta_pos = abs(cur_pos-abs_position)
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(delta_pos)

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
        if rel_position < 0:
            cmd_string = 'D{0}'.format(abs(rel_position))
        else:
            cmd_string = 'P{0}'.format(rel_position)
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(rel_position))

    # Chainable set commands
    @execWrap
    def setSpeed(self, speed_code):
        if not 0 <= speed_code <= 40:
            raise(ValueError('`speed_code` [{0}] must be between 0 and 40'
                             ''.format(speed_code)))
        cmd_string = 'S{0}'.format(speed_code)
        self.sim_speed_change = True
        self._simIncToPulses(speed_code)
        self.cmd_chain += cmd_string

    @execWrap
    def setStartSpeed(self, pulses_per_sec):
        if not 50 <= pulses_per_sec <= 1000:
            raise(ValueError('Start speed `pulses_per_sec` [{0}] must be '
                             'between 50 and 1000'.format(pulses_per_sec)))
        cmd_string = 'v{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setTopSpeed(self, pulses_per_sec):
        if not 5 <= pulses_per_sec <= 6000:
            raise(ValueError('Cutoff speed `pulses_per_sec` [{0}] must be '
                             'between 5 and 6000'.format(pulses_per_sec)))
        cmd_string = 'V{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setCutoffSpeed(self, pulses_per_sec):
        if not 50 <= pulses_per_sec <= 2700:
            raise(ValueError('Cutoff speed `pulses_per_sec` [{0}] must be '
                             'between 50 and 2700'.format(pulses_per_sec)))
        cmd_string = 'c{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setSlope(self, slope_code, chain=False):
        if not 1 <= slope_code <= 20:
            raise(ValueError('`slope_code` [{0}] must be between 1 and 20'
                             ''.format(slope_code)))
        cmd_string = 'L{0}'.format(slope_code)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    # Chainable control commands

    @execWrap
    def repeatCmdSeq(self, num_repeats):
        if not 0 < num_repeats < 30000:
            raise(ValueError('`num_repeats` [{0}] must be between 0 and 30000'
                             ''.format(num_repeats)))
        cmd_string = 'G{0}'.format(num_repeats)
        self.cmd_chain += cmd_string
        self.exec_time *= num_repeats

    @execWrap
    def markRepeatStart(self):
        cmd_string = 'g'
        self.cmd_chain += cmd_string

    @execWrap
    def delayExec(self, delay_ms):
        """ Delays command execution for `delay` milliseconds """
        if not 0 < delay < 30000:
            raise(ValueError('`delay` [{0}] must be between 0 and 40000 ms'
                             ''.format(delay)))
        cmd_string = 'M{0}'.format(delay)
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
        if not 0 <= input_pin < 2:
            raise(ValueError('`input_pin` [{0}] must be between 0 and 2'
                             ''.format(input_sig)))
        cmd_string = 'H{0}'.format(input_sig)
        return self.sendRcv(cmd_string)

    # Report commands

    def updateSpeeds(self):
        self.getStartSpeed()
        self.getTopSpeed()
        self.getCutoffSpeed()

    def getPlungerPos(self):
        """ Returns the absolute plunger position as an int (0-3000) """
        cmd_string = '?'
        data = self.sendRcv(cmd_string)
        return int(data)

    def getStartSpeed(self):
        """ Returns the start speed as an int (in pulses/sec) """
        cmd_string = '?1'
        data = self.sendRcv(cmd_string)
        self.state['start_speed'] = int(data)
        return self.state['start_speed']

    def getTopSpeed(self):
        """ Returns the top speed as an int (in pulses/sec) """
        cmd_string = '?2'
        data = self.sendRcv(cmd_string)
        self.state['top_speed'] = int(data)
        return self.state['top_speed']

    def getCutoffSpeed(self):
        """ Returns the cutoff speed as an int (in pulses/sec) """
        cmd_string = '?3'
        data = self.sendRcv(cmd_string)
        self.state['cutoff_speed'] = int(data)
        return self.state['cutoff_speed']

    def getEncoderPos(self):
        """ Returns the current encoder count on the plunger axis """
        cmd_string = '?4'
        data = self.sendRcv(cmd_string)
        return int(data)

    def getCurPort(self):
        """ Returns the current port position (1-num_ports) """
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
        cmd_string = '?10'
        data = self.sendRcv(cmd_string)
        return int(data)

    # Config commands

    def setMicrostep(self, on=False):
        """ Turns microstep mode on or off """
        cmd_string = 'N{0}'.format(int(on))
        self.sendRcv(cmd_string, execute=True)
        self.microstep = on

    # Control commands

    def terminateCmd(self):
        cmd_string = 'T'
        return self.sendRcv(cmd_string, execute=True)

    # Communication handlers and special functions

    def waitReady(self, timeout=10, polling_interval=0.3):
        self._waitReady(timeout=10, polling_interval=0.3)

    @contextmanager
    def _syringeErrorHandler(self):
        """
        Context manager to handle `SyringeError` based on error code. Right
        now this just handles "Device Not Initialized" errors (code 7) by
        initializing the pump and then re-running the previous command.
        """
        try:
            yield
        except SyringeError, e:
            if e.err_code == 7:
                try:
                    self.init()
                except SyringeError, e:
                    if e.err_code == 7:
                        pass
                    else:
                        raise e
                self.waitBusy()
                self.sendRcv(self.last_cmd)
            else:
                self.resetChain()
                raise e
        except Exception, e:
            self.resetChain()
            raise e

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

        if execute:
            cmd_string += 'R'
        self.last_cmd = cmd_string
        with self._syringeErrorHandler():
            parsed_response = super(XCaliburD, self)._sendRcv(cmd_string)
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
        if not microstep: microstep = self.state['microstep']
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
