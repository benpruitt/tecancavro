from tecancavro.models import XCaliburD

from tecancavro.transport import TecanAPISerial


def returnCavro():
    testO = XCaliburD(com_link=TecanAPISerial(0, '/dev/ttyUSB0', 9600))
    return testO
