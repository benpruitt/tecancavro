from flask import Flask, render_template, current_app, request
from flask import json, jsonify, make_response, session, send_from_directory
from flask import redirect, url_for, escape, make_response

# Create and configure out application.
app = Flask(__name__)
app.config.from_object(__name__)

app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

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

device_dict = {x[0]:x[1] for x in devices}


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
def main():
    global devices
    # the valve count is in the 2nd field of
    # each item in devices e.g "9dist"
    valves=list(range(1,10))
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    return render_template('main.html', params=params)

@app.route('/pull')
def pull_call():
    global device_dict
    val = request.args['value']
    sp = request.args['serial_port']
    print("got", val, sp)
    # device_dict[sp].doSomething(val)
    return ('', 204)

@app.route('/push')
def push_call():
    global device_dict
    val = request.args['value']
    sp = request.args['serial_port']
    print("got", val, sp)
    # device_dict[sp].doSomething(val)
    return ('', 204)

if __name__ == '__main__':
    app.debug = True
    app.run()
    # app.run(host='0.0.0.0')