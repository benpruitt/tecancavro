from __future__ import print_function

from flask import Flask, render_template, current_app, request
from flask import json, jsonify, make_response, session, send_from_directory
from flask import redirect, url_for, escape, make_response
from flask_bootstrap import Bootstrap
import sqlite3

# Create and configure out application.
SPEED_CODES_STROKE = {0: 1.25, 1: 1.3, 2: 1.39, 3: 1.52, 4: 1.71, 5: 1.97,
                          6: 2.37, 7: 2.77, 8: 3.03, 9: 3.36, 10: 3.77, 11: 4.3,
                          12: 5.0, 13: 6.0, 14: 7.5, 15: 10.0, 16: 15.0, 17: 30.0,
                          18: 31.58, 19: 33.33, 20: 35.29, 21: 37.50, 22: 40.0, 23: 42.86,
                          24: 46.15, 25: 50.0, 26: 54.55, 17: 60.0, 28: 66.67, 29: 75.0,
                          30: 85.71, 31: 100.0, 32: 120.0, 33: 150.0, 34: 200.0, 35: 300.0, 36: 333.33,
                          37: 375.0, 38: 428.57, 39: 500.0, 40: 600.0}

app = Flask(__name__)
app.config.from_object(__name__)
Bootstrap(app)


app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True


# Insert a row of data
#c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")

# Save (commit) the changes
#conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
#conn.close()

try:
    from tecancavro.models import XCaliburD
    from tecancavro.transport import TecanAPISerial, TecanAPINode
except ImportError:  # Support direct import from package
    import sys
    import os
    dirn = os.path.dirname
    LOCAL_DIR = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(dirn(dirn(LOCAL_DIR)))
    from tecancavro.models import XCaliburD
    from tecancavro.transport import TecanAPISerial, TecanAPINode

def findSerialPumps():
    return TecanAPISerial.findSerialPumps()
def _rateToSpeed(rate_ul_s):
        """
        Converts a rate in microliters/seconds (ul/sec) to Speed Code.

        Args:
            `volume_ul` (int) : volume in microliters
        Kwargs:
            `microstep` (bool) : whether to convert to standard steps or
                                 microsteps

        """
        #CHANGE TO MAKE BETTER STYLE
        target_sec_per_stroke = 5000/rate_ul_s
        closest_ind = 0
        closest_val = SPEED_CODES_STROKE[closest_ind]
        for item in SPEED_CODES_STROKE:
            if(abs(SPEED_CODES_STROKE[item] - target_sec_per_stroke) < abs(SPEED_CODES_STROKE[closest_ind] - target_sec_per_stroke)):
                closest_ind = item
                closest_val = SPEED_CODES_STROKE[item]

        return closest_ind


def getSerialPumps():
    ''' Assumes that the pumps are XCaliburD pumps and returns a list of
    (<serial port>, <instantiated XCaliburD>) tuples
    '''
    pump_list = findSerialPumps()
    return [(ser_port, XCaliburD(com_link=TecanAPISerial(0,
             ser_port, 9600))) for ser_port, _, _ in pump_list]

devices = getSerialPumps()
device_dict = dict(devices)
for item in devices:
    device_dict[item[0]].init()
    device_dict[item[0]].setSpeed(25)
    device_dict[item[0]].primePort(1,500)
    device_dict[item[0]].primePort(2,500)
    device_dict[item[0]].primePort(3,500)
    device_dict[item[0]].primePort(4,500)
    device_dict[item[0]].primePort(6,500)
    device_dict[item[0]].primePort(7,500)
    device_dict[item[0]].primePort(8,500)

#def get_resource_as_string(name, charset='utf-8'):
 #   with app.open_resource(name) as f:
  #      return f.read().decode(charset)

#url_for('static', filename='js/jquery.js')
#url_for('static', filename='js/bootstrap.min.js')
#url_for('static', filename='js/plugins/morris/raphael.min.js')
#url_for('static', filename='js/plugins/morris/morris.min.js')
#url_for('static', filename='js/plugins/morris/morris-data.js')



#app.jinja_env.globals['get_resource_as_string'] = get_resource_as_string




###############################################################################
# Error handlers
###############################################################################

# @app.errorhandler(404)
# def page_not_found(error, errormessage=""):
#     return render_template('error404.html', message=errormessage), 404


# @app.errorhandler(500)
# def server_problem(error):
#     return render_template('error500.html', message=error), 500

@app.route('/')
def index():
    global devices
    # the valve count is in the 2nd field of
    # each item in devices e.g "9dist"
    valves=list(range(1,10))
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    return render_template('index.html', params=params)

@app.route('/Simple_Commands')
def Simple_Commands():
    global devices
    # the valve count is in the 2nd field of
    # each item in devices e.g "9dist"
    valves=list(range(1,10))
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    return render_template('Simple_Commands.html', params=params)

@app.route('/Protocol')
def Protocol():
    global devices
    # the valve count is in the 2nd field of
    # each item in devices e.g "9dist"
    valves=list(range(1,10))
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    return render_template('Protocol.html', params=params)

@app.route('/extract')
def extract_call():
    global device_dict
    volume = int(request.args['volume'])
    port = int(request.args['port'])
    sp = request.args['serial_port']
    rate = int(request.args['rate'])
    if(rate != 0 and len(sp) > 0):
        newSpeed = _rateToSpeed(rate)
        #device_dict[sp].setSpeed(newSpeed)
        print("Speed Calc")
        print(rate)
        print(newSpeed)

    #print("here")
    willex = int(request.args['exec'])
    if(willex == 0):
        executing = False
    else:
        executing = True
    print(executing)
    print("Received extract for: %d ul from port %d on serial port %s" % (volume,
          port, sp))
    if len(sp) > 0:
        device_dict[sp].extract(port, volume, speed = newSpeed, execute = executing)
    # device_dict[sp].doSomething(val)
    return ('', 204)

@app.route('/dispense')
def dispense_call():
    global device_dict
    volume = int(request.args['volume'])
    port = int(request.args['port'])
    sp = request.args['serial_port']
    rate = int(request.args['rate'])
    if(rate != 0 and len(sp) > 0):
        newSpeed = _rateToSpeed(rate)
        #device_dict[sp].setSpeed(newSpeed)
        print("Speed Calc")
        print(rate)
        print(newSpeed)

    willex = int(request.args['exec'])
    if(willex == 0):
        executing = False
    else:
        executing = True
    print("Received dispense for: %d ul from port %d on serial port %s" % (volume,
          port, sp))
    if len(sp) > 0:
        device_dict[sp].dispense(port, volume, speed = newSpeed, execute = executing)
    return ('', 204)

@app.route('/execute')
def execute_call():
    global device_dict
    sp = request.args['serial_port']
    print("executing chain")
    if len(sp) > 0:
        device_dict[sp].executeChain()
    return ('', 204)

@app.route('/tables')
def tables():
    return render_template('tables.html')

if __name__ == '__main__':
    app.debug = True
    
    #app.run()
    app.run(host='0.0.0.0')

