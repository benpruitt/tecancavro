from tecancavro.models import XCaliburD

from tecancavro.transport import TecanAPISerial, TecanAPINode

# Functions to return instantiated XCaliburD objects for testing

SPEED_CODES_STROKE = {0: 1.25, 1: 1.3, 2: 1.39, 3: 1.52, 4: 1.71, 5: 1.97,
                          6: 2.37, 7: 2.77, 8: 3.03, 9: 3.36, 10: 3.77, 11: 4.3,
                          12: 5.0, 13: 6.0, 14: 7.5, 15: 10.0, 16: 15.0, 17: 30.0,
                          18: 31.58, 19: 33.33, 20: 35.29, 21: 37.50, 22: 40.0, 23: 42.86,
                          24: 46.15, 25: 50.0, 26: 54.55, 17: 60.0, 28: 66.67, 29: 75.0,
                          30: 85.71, 31: 100.0, 32: 120.0, 33: 150.0, 34: 200.0, 35: 300.0, 36: 333.33,
                          37: 375.0, 38: 428.57, 39: 500.0, 40: 600.0}

def returnSerialXCaliburD():
    test0 = XCaliburD(com_link=TecanAPISerial(0, '/dev/tty.usbserial', 9600))
    return test0

def returnNodeXCaliburD():
	test0 = XCaliburD(com_link=TecanAPINode(0, '192.168.1.140:80'), waste_port=6)
	return test0

def findSerialPumps():
    return TecanAPISerial.findSerialPumps()

def getSerialPumps():
    ''' Assumes that the pumps are XCaliburD pumps and returns a list of
    (<serial port>, <instantiated XCaliburD>) tuples
    '''
    pump_list = findSerialPumps()
    return [(ser_port, XCaliburD(com_link=TecanAPISerial(0,
             ser_port, 9600))) for ser_port, _, _ in pump_list]
def _rateToSpeed(volume_ul, rate_ul_s):
        """
        Converts a rate in microliters/seconds (ul/sec) to Speed Code.

        Args:
            `volume_ul` (int) : volume in microliters
        Kwargs:
            `microstep` (bool) : whether to convert to standard steps or
                                 microsteps

        """
        target_sec_per_stroke = volume_ul/rate_ul_s
        closest_ind = 0
        closest_val = SPEED_CODES_STROKE[closest_ind]
        for item in SPEED_CODES_STROKE:
            if(abs(SPEED_CODES_STROKE[item] - target_sec_per_stroke) < abs(SPEED_CODES_STROKE[closest_ind] - target_sec_per_stroke)):
                closest_ind = item
                closest_val = SPEED_CODES_STROKE[item]

        return closest_ind


if __name__ == '__main__':
    print(findSerialPumps())