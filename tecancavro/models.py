"""
models.py

Contains Tecan Cavro model-specific classes that inherit from the `Syringe`
class in syringe.py.

"""

from math import sqrt
from time import sleep
from functools import wraps

from syringe import Syringe, SyringeError, SyringeTimeout


class XCaliburD(Syringe):
    """
    Class to control XCalibur pumps with distribution valves. Provides front-
    end validation and convenience functions (e.g. smartExtract) -- see
    individual docstrings for more information.
    """

    DIR_DICT = {'CW': ('I', 'Z'), 'CCW': ('O', 'Y')}

    def __init__(self, com_link, num_ports=9, syringe_ul=1000,
                 microstep=False, waste_port=None, slope=7):
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
                [default] - None
            `slope` (int) : slope setting
                [default] - 7 (factory default)

        """
        super(XCaliburD, self).__init__(com_link)
        self.num_ports = 9
        self.syringe_ul = 1000
        self.waste_port = waste_port
        self.state = {
            'microstep': microstep,
            'start_speed': None,
            'top_speed': None,
            'cutoff_speed': None,
            'slope': 7
        }
        # Command chaining state information
        self.cmd_chain = ''
        self.exec_time = 0
        self.sim_speed_change = False
        self.sim_state = {k: v for k,v in self.state.iteritems()}

        # Init functions
        self.updateSpeeds()
        self.updateSimState()

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
            self.resetChain()
            self.waitReady()
            self.changePort(out_port, from_port=in_port)
            self.cacheSimSpeeds()
            self.setSpeed(0)
            self.movePlungerAbs(0)
            self.changePort(in_port, from_port=out_port)
            self.restoreSimSpeeds()
            self.movePlungerRel(steps)
            return self.executeChain()

    # Chain functions

    def executeChain(self):
        """
        Executes and resets the current command chain (`self.cmd_chain`).
        Returns the estimated execution time (`self.exec_time`) for the chain.

        """
        self._sendRcv(self.cmd_chain, execute=True)
        exec_time = self.exec_time
        self.resetChain(on_execute=True)
        return exec_time

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
        if from_port:
            diff = to_port - from_port
            if abs(diff) >= 7: diff = -diff
            if diff < 0: direction = 'CCW'
            else: direction = 'CW'
        cmd_string = '{0}{1}'.format(XCaliburD.DIR_DICT[direction][0], to_port)
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
            cmd_string = 'D{0}'.format(rel_position)
        else:
            cmd_string = 'P{0}'.format(rel_position)
        self.cmd_chain += cmd_string
        self.exec_time += self._calcPlungerMoveTime(abs(rel_position))

    # Chainable set commands
    @execWrap
    def setSpeed(self, increments):
        cmd_string = 'S{0}'.format(increments)
        self.sim_speed_change = True
        #self._simIncToPulses()
        self.cmd_chain += cmd_string

    @execWrap
    def setStartSpeed(self, pulses_per_sec):
        cmd_string = 'v{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setTopSpeed(self, pulses_per_sec):
        cmd_string = 'V{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setCutoffSpeed(self, pulses_per_sec):
        cmd_string = 'c{0}'.format(pulses_per_sec)
        self.sim_speed_change = True
        self.cmd_chain += cmd_string

    @execWrap
    def setSlope(self, slope_code, chain=False):
        if not 1 <= slope_code <= 20:
            raise(ValueError('`slope_code` [{0}] must be between 0 and 20'
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
        cmd_string = 'G{0}'.num_repeats
        self.cmd_chain += cmd_string
        self.delay *= num_repeats

    @execWrap
    def delayExec(self, delay_ms):
        """ Delays command execution for `delay` milliseconds """
        if not 0 < delay < 30000:
            raise(ValueError('`delay` [{0}] must be between 0 and 40000 ms'
                             ''.format(delay)))
        cmd_string = 'M{0}'.format(delay)
        self.cmd_chain += cmd_string

    # Report commands

    def updateSpeeds(self):
        self.getStartSpeed()
        self.getTopSpeed()
        self.getCutoffSpeed()

    def getPlungerPos(self):
        """ Returns the absolute plunger position as an int (0-3000) """
        cmd_string = '?'
        parsed_response = self._sendRcv(cmd_string)
        return int(parsed_response[0])

    def getStartSpeed(self):
        """ Returns the start speed as an int (in pulses/sec) """
        cmd_string = '?1'
        parsed_response = self._sendRcv(cmd_string)
        self.state['start_speed'] = int(parsed_response[0])
        return self.state['start_speed']

    def getTopSpeed(self):
        """ Returns the top speed as an int (in pulses/sec) """
        cmd_string = '?2'
        parsed_response = self._sendRcv(cmd_string)
        self.state['top_speed'] = int(parsed_response[0])
        return self.state['top_speed']

    def getCutoffSpeed(self):
        """ Returns the cutoff speed as an int (in pulses/sec) """
        cmd_string = '?3'
        parsed_response = self._sendRcv(cmd_string)
        self.state['cutoff_speed'] = int(parsed_response[0])
        return self.state['cutoff_speed']

    def getEncoderPos(self):
        """ Returns the current encoder count on the plunger axis """
        cmd_string = '?4'
        parsed_response = self._sendRcv(cmd_string)
        return int(parsed_response[0])

    def getCurPort(self):
        """ Returns the current port position (1-num_ports) """
        cmd_string = '?6'
        parsed_response = self._sendRcv(cmd_string)
        return int(parsed_response[0])

    def getBufferStatus(self):
        """ Returns the current cmd buffer status (0=empty, 1=non-empty) """
        cmd_string = '?10'
        parsed_response = self._sendRcv(cmd_string)
        return int(parsed_response[0])

    # Control commands

    def terminateCmd(self):
        cmd_string = 'T'
        return self._sendRcv(cmd_string, execute=True)

    def haltExec(self, input_sig=0):
        if not 0 < input_sig < 2:
            raise(ValueError('`input_sig` [{0}] must be between 0 and 2'
                             ''.format(input_sig)))
        cmd_string = 'H{0}'.format(input_sig)
        return self._sendRcv(cmd_string)

    # Communication handlers and special functions

    def waitReady(self, timeout=10, polling_interval=0.3):
        self._waitReady(timeout=10, polling_interval=0.3)

    def _sendRcv(self, cmd_string, execute=False):
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
        parsed_response = super(XCaliburD, self).sendRcv(cmd_string)
        return parsed_response

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
            `microstep` (bool) : whether to convert to standard steps or microsteps

        """
        if not microstep: microstep = self.state['microstep']
        if microstep:
            steps = volume_ul * (24000/self.syringe_ul)
        else:
            steps = volume_ul * (3000/self.syringe_ul)
        return steps

    def __del__(self):
        """
        Upon object deletion (e.g. after a KeyboardInterrupt), the current
        command execution is terminated

        """
        self.terminateCmd()