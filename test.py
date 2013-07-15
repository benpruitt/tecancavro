from tecancavro.models import XCaliburD

from tecancavro.transport import TecanAPISerial, TecanAPINode


def returnCavro():
    testO = XCaliburD(com_link=TecanAPISerial(0, '/dev/ttyUSB0', 9600))
    return testO

def httpTest():
	test0 = XCaliburD(com_link=TecanAPINode(0, '192.168.1.140:80'), waste_port=6)
	return test0