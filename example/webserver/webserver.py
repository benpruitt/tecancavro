from __future__ import print_function

from flask import Flask, render_template, current_app, request
from flask import json, jsonify, make_response, session, send_from_directory
from flask import redirect, url_for, escape, make_response
from flask_bootstrap import Bootstrap

# Create and configure out application.

app = Flask(__name__)
app.config.from_object(__name__)
Bootstrap(app)


app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

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


def getSerialPumps():
    ''' Assumes that the pumps are XCaliburD pumps and returns a list of
    (<serial port>, <instantiated XCaliburD>) tuples
    '''
    pump_list = findSerialPumps()
    return [(ser_port, XCaliburD(com_link=TecanAPISerial(0,
             ser_port, 9600))) for ser_port, _, _ in pump_list]

devices = getSerialPumps()
device_dict = dict(devices)

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
    print("Received extract for: %d ul from port %d on serial port %s" % (volume,
          port, sp))
    if len(sp) > 0:
        device_dict[sp].extract(port, volume)
    # device_dict[sp].doSomething(val)
    return ('', 204)

@app.route('/dispense')
def dispense_call():
    global device_dict
    volume = int(request.args['volume'])
    port = int(request.args['port'])
    sp = request.args['serial_port']
    print("Received dispense for: %d ul from port %d on serial port %s" % (volume,
          port, sp))
    if len(sp) > 0:
        device_dict[sp].dispense(port, volume)
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
    
    app.run()
    # app.run(host='0.0.0.0')