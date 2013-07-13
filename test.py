from tecancavro.models import XCaliburD

from tecancavro.tecanapi import SerialAPILink


def returnCavro():
    testO = XCaliburD(com_link=SerialAPILink(0, '/dev/ttyUSB0', 9600))
    return testO
