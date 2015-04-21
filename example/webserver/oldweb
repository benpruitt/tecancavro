from __future__ import print_function

from flask import Flask, render_template, current_app, request
from flask import json, jsonify, make_response, session, send_from_directory
from flask import redirect, url_for, escape, make_response
from flask_bootstrap import Bootstrap
import sqlite3
from celery import Celery
import hashlib
import uuid
import json
#from passlib.apps import custom_app_context as pwd_context
import datetime
from werkzeug.security import generate_password_hash, \
     check_password_hash
import pytz
from pytz import timezone
 
PUMP_VOLUME_UL = 5000.0
EXTRACT_SPEED = 15

class User(object):

    def __init__(self, username, password):
        self.username = username
        self.set_password(password)

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)     


# Create and configure out application.
SPEED_CODES_STROKE = {0: 1.25, 1: 1.3, 2: 1.39, 3: 1.52, 4: 1.71, 5: 1.97,
                          6: 2.37, 7: 2.77, 8: 3.03, 9: 3.36, 10: 3.77, 11: 4.3,
                          12: 5.0, 13: 6.0, 14: 7.5, 15: 10.0, 16: 15.0, 17: 30.0,
                          18: 31.58, 19: 33.33, 20: 35.29, 21: 37.50, 22: 40.0, 23: 42.86,
                          24: 46.15, 25: 50.0, 26: 54.55, 17: 60.0, 28: 66.67, 29: 75.0,
                          30: 85.71, 31: 100.0, 32: 120.0, 33: 150.0, 34: 200.0, 35: 300.0, 36: 333.33,
                          37: 375.0, 38: 428.57, 39: 500.0, 40: 600.0}
FIXED_NUMBER_BREAKS_OPTION = 0
FIXED_BREAK_INTERVAL_OPTION = 1
MIMIC_HEARTBEAT_OPTION = 2
CONTANT_FLOW_OPTION = 3

OPTION_TO_USE = CONTANT_FLOW_OPTION
ALLOW_CONSTANT = True



app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task
def testFunc():
    print("TESTTESTESTESTETS")

current_user = None
current_user_id = None



Bootstrap(app)


app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

#salt = uuid.uuid4().hex
#hashed_password = hashlib.sha512(password + salt).hexdigest()




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
        target_sec_per_stroke = 5000.0/float(rate_ul_s)
        closest_ind = 0
        closest_val = SPEED_CODES_STROKE[closest_ind]
        for item in SPEED_CODES_STROKE:
            if(abs(SPEED_CODES_STROKE[item] - target_sec_per_stroke) < abs(SPEED_CODES_STROKE[closest_ind] - target_sec_per_stroke)):
                closest_ind = item
                closest_val = SPEED_CODES_STROKE[item]
        print("Target:")
        print(target_sec_per_stroke)
        print("ACtual:")
        print(closest_val)
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
    #device_dict[item[0]].primePort(1,500)
    #device_dict[item[0]].primePort(2,500)
    #device_dict[item[0]].primePort(3,500)
    #device_dict[item[0]].primePort(4,500)
    #device_dict[item[0]].primePort(6,500)
    #device_dict[item[0]].primePort(7,500)
    #device_dict[item[0]].primePort(8,500)

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
def Simple_Commands():
    global device_dict, current_user, devices,current_user_id
    if(current_user == None):
        #global devices
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params=params)

    else:
        
        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Simple_Commands.html', params=params)

@app.route('/Protocol')
def Protocol():
    global device_dict, current_user,current_user_id
    if(current_user == None):
        params = {}
        #params['valves'] = valves
        #params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params=params)
    else:
        global devices
        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Protocol.html', params = params)
@app.route('/AdvancedProtocol')
def AdvancedProtocol():
    global device_dict, current_user, devices,current_user_id
    if(current_user == None):

        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params=params)
    else:
        
        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['username'] = current_user
        params['devices'] = devices
        return render_template('AdvancedProtocol.html', params=params)

@app.route('/AdvancedProtocol2')
def AdvancedProtocol2():
    global device_dict, current_user, devices,current_user_id
    if(current_user == None):

        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params=params)
    else:
        protocol = request.args['id']
        print(protocol)
        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['username'] = current_user
        params['devices'] = devices
        conn = sqlite3.connect('Raspi.db')
        c = conn.cursor()
        protocolsnew = []
        prots = c.execute("SELECT * FROM Protocols2 WHERE protocolID = ?", [protocol])
        for row in prots:
            print(row)
            number = str(row[1])
            rate = row[2]
            vol = row[3]
            fromid = row[4]
            toid = row[5]
            protocolsnew.append({"num":number,"rate":rate,"vol":vol, "fromid": fromid, "toid":toid})

        params['protocols'] = protocolsnew
        
        

        conn.commit()
        conn.close()
        return render_template('AdvancedProtocol2.html', params=params)


@app.route('/extract')
def extract_call():
    global device_dict, current_user,current_user_id
    volume = int(request.args['volume'])
    port = int(request.args['port'])
    sp = request.args['serial_port']
    rate = int(request.args['rate'])
    #testFunc.apply_async(args=[msg],countdown = 15)
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
    global device_dict, current_user,current_user_id
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
def execute_chain():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
    print("executing chain")
    if len(sp) > 0:
        device_dict[sp].executeChain()
    return ('', 204)
@app.route('/halt')
def halt():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
    print("halting chain")
    if len(sp) > 0:
        device_dict[sp].haltExec()
        device_dict[sp].resetChain()
    return ('', 204)

@app.route('/advProtocol')
def advProtocol():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
    numitems = int(request.args['numitems'])
    fromports =  json.loads(request.args['fromports'])
    toports =  json.loads(request.args['toports'])
    finalports =  json.loads(request.args['finals'])
    datetimes = json.loads(request.args['datetimes'])
    flowrates =  json.loads(request.args['flowrates'])
    volumes =  json.loads(request.args['volumes'])
    conn = sqlite3.connect('Raspi.db')
    c = conn.cursor()
    #change to make use unused numbers not max
    c.execute("SELECT MAX(protocolID) FROM Protocols2")
    maxid = int(c.fetchone()[0])
    newid = maxid+1
    print("Newid: %d", newid)
    for i in range(0,numitems):
        items = [newid, (i+1), flowrates[i], volumes[i], fromports[i],toports[i],datetimes[i]]
        c.execute("INSERT INTO Protocols2 VALUES (?,?,?,?,?,?,?)", items)
        print("i")

    #get current user
    curr_user = 1
    import time
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    items = [st, st, current_user_id, newid]
    print(st)
    c.execute("INSERT INTO UserProtocols3 VALUES (?,?,?,?)", items)
    print("Added")

    conn.commit()
    conn.close()
    for i in range(0,numitems):
        print(int(datetimes[i][0:4]))
        print(int(datetimes[i][5:7]))
        print(int(datetimes[i][8:10]))
        print(int(datetimes[i][11:13]))
        print(int(datetimes[i][14:16]))
        print(int(datetimes[i][17:19]))
        dt = datetime.datetime(int(datetimes[i][0:4]), int(datetimes[i][5:7]), int(datetimes[i][8:10]), int(datetimes[i][11:13]), int(datetimes[i][14:16]), int(datetimes[i][17:19]), 0)
        print(dt)
        eastern = timezone('US/Eastern')
        dt = eastern.localize(dt)
        createTask(int(fromports[i]), int(toports[i]), int(finalports[i]), float(flowrates[i]), float(volumes[i]), sp, dt)
    return ('', 204)

def createTask(from_port_id, to_port_id, final_port_id, flowrate_ul_s, volume_ul, serial_port, datetime_execute):
    if(len(serial_port) >= 0):
        speed_to_use = 0
        if(flowrate_ul_s != 0):
            speed_to_use = _rateToSpeed(flowrate_ul_s)
        else:
            return "ERROR"

        actual_rate_ul_s = PUMP_VOLUME_UL / float(SPEED_CODES_STROKE[speed_to_use])
        target_time_s = volume_ul / flowrate_ul_s
        actual_time_s = volume_ul / actual_rate_ul_s
        if(ALLOW_CONSTANT and target_time_s == actual_time_s and volume_ul <= PUMP_VOLUME_UL):
            performtask.apply_async(args =[from_port_id, to_port_id, actual_rate_ul_s, volume_ul,serial_port,speed_to_use], eta = datetime_execute)
        else:
            if actual_time_s >= target_time_s:
                print("hi")
            if speed_to_use == 0:
                error_message = "Could not complete with bounds specified, pump does not have a rate that is fast enough"
                print(error_message)
                return error_message
            else:
                speed_to_use = speed_to_use - 1
                actual_rate_ul_s = PUMP_VOLUME_UL / float(SPEED_CODES_STROKE[speed_to_use])
                actual_time_s = volume_ul / actual_rate_ul_s
            print("her")
            pulsatile_flowrate_options[OPTION_TO_USE](from_port_id, to_port_id,final_port_id, flowrate_ul_s, actual_rate_ul_s, actual_time_s, speed_to_use, target_time_s, volume_ul, serial_port, datetime_execute)

def fixed_number_breaks(from_port_id, to_port_id, final_port_id,flowrate_ul_s, actual_rate_ul_s, actual_time_s, speed_to_use, target_time_s, volume_ul, serial_port, datetime_execute, numbreaks = 100):
    time_to_makeup_s = target_time_s - actual_time_s
    assert time_to_makeup_s > 0

    time_per_break = time_to_makeup_s/numbreaks

    ##ADD TIME TO SWITCH PORT
    if(time_per_break < SPEED_CODES_STROKE[EXTRACT_SPEED]):
        error_message = "Cannot complete with bounds specified, not enough time during breaks to refill"
        print(error_message)
        return error_message

    time_per_execution = actual_time_s / numbreaks
    volume_per_execution = time_per_execution * actual_rate_ul_s
    breaks = [0]
    executions = [time_per_break]
    for i in range(0, numbreaks-1): # build arrays for start times of breaks and executions
        breaks.append(executions[i] + time_per_execution)
        executions.append(breaks[i+1] + time_per_break)

def fixed_break_interval(from_port_id, to_port_id, final_port_id,flowrate_ul_s, actual_rate_ul_s, actual_time_s, speed_to_use, target_time_s, volume_ul, serial_port, datetime_execute, numbreaks = 100):
    print("hi")
def mimic_heartbeat(from_port_id, to_port_id, final_port_id,flowrate_ul_s, actual_rate_ul_s, actual_time_s, speed_to_use, target_time_s, volume_ul, serial_port, datetime_execute, numbreaks = 100):
    print("hi")
                      


    # else:
    #             volume_remaining = volume_ul
    #             next_dt = datetime_execute
    #             while volume_remaining > 0:
    #                 if volume_remaining >= PUMP_VOLUME_UL:
    #                     performtask.apply_async(args =[from_port_id, to_port_id, flowrate_ul_s, PUMP_VOLUME_UL, serial_port, speed_to_use], eta = next_dt)
    #                     volume_remaining = volume_remaining - PUMP_VOLUME_UL
    #                 else:
    #                     performtask.apply_async(args =[from_port_id, to_port_id, flowrate_ul_s, volume_remaining, serial_port, speed_to_use], eta = next_dt)
    #                     volume_remaining = 0

def constant_flow(from_port_id, to_port_id, final_port_id,flowrate_ul_s, actual_rate_ul_s, actual_time_s, speed_to_use, target_time_s, volume_ul, serial_port, datetime_execute):
    if(target_time_s == actual_time_s and volume_ul <= PUMP_VOLUME_UL):
        performtask.apply_async(args =[from_port_id, to_port_id, actual_rate_ul_s, volume_ul,serial_port,speed_to_use], eta = datetime_execute)
        if(final_port_id != 0):
            time_for_task = volume_ul / actual_rate_ul_s + (2 * SPEED_CODES_STROKE[EXTRACT_SPEED])
            next_dt = datetime_execute + datetime.timedelta(0,time_for_task)
            print(final_port_id)
            performtask.apply_async(args =[9, int(final_port_id), actual_rate_ul_s, PUMP_VOLUME_UL, serial_port, EXTRACT_SPEED], eta = next_dt)

    else:
        volume_remaining = volume_ul
        next_dt = datetime_execute
        while volume_remaining > 0:
            print(next_dt)
            if volume_remaining >= PUMP_VOLUME_UL:
                performtask.apply_async(args =[from_port_id, to_port_id, actual_rate_ul_s, PUMP_VOLUME_UL, serial_port, speed_to_use], eta = next_dt)
                volume_remaining = volume_remaining - PUMP_VOLUME_UL
                time_for_task = PUMP_VOLUME_UL / flowrate_ul_s + (3 * SPEED_CODES_STROKE[EXTRACT_SPEED])
                next_dt = next_dt + datetime.timedelta(0,time_for_task)
                print(final_port_id)
                if(final_port_id != 0):
                    performtask.apply_async(args =[9, int(final_port_id), actual_rate_ul_s, PUMP_VOLUME_UL, serial_port, EXTRACT_SPEED], eta = next_dt)
                    time_for_task = (4 * SPEED_CODES_STROKE[EXTRACT_SPEED])
                    next_dt = next_dt + datetime.timedelta(0,time_for_task)
            else:
                performtask.apply_async(args =[from_port_id, to_port_id, actual_rate_ul_s, volume_remaining, serial_port, speed_to_use], eta = next_dt)
                volume_remaining = 0
                time_for_task = volume_remaining / flowrate_ul_s + (3 * SPEED_CODES_STROKE[EXTRACT_SPEED])
                next_dt = next_dt + datetime.timedelta(0,time_for_task)
                print(final_port_id)
                if(final_port_id != 0):
                    performtask.apply_async(args =[9, int(final_port_id), actual_rate_ul_s, PUMP_VOLUME_UL, serial_port, EXTRACT_SPEED], eta = next_dt)
                    


pulsatile_flowrate_options = {0 : fixed_number_breaks,
                              1 : fixed_break_interval,
                              2 : mimic_heartbeat,
                              3 : constant_flow
}
    
@celery.task
def performtask(from_id, to_id, rate_ul_s, vol_ul,sp,speed_to_use):
    global device_dict, current_user,current_user_id

    if len(sp) > 0:
        device_dict[sp].resetChain()
        print(vol_ul)
        device_dict[sp].extract(int(from_id), int(vol_ul), speed = EXTRACT_SPEED)
        print(vol_ul)
        device_dict[sp].dispense(int(to_id), int(vol_ul), speed = speed_to_use)
        print(vol_ul)
        device_dict[sp].executeChain()

    print("Performing Task")

@app.route('/saveProtocol')
def saveProtocol():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
    numitems = int(request.args['numitems'])
    fromports =  json.loads(request.args['fromports'])
    toports =  json.loads(request.args['toports'])
    datetimes = json.loads(request.args['datetimes'])
    flowrates =  json.loads(request.args['flowrates'])
    volumes =  json.loads(request.args['volumes'])
    conn = sqlite3.connect('Raspi.db')
    c = conn.cursor()
    #change to make use unused numbers not max
    c.execute("SELECT MAX(protocolID) FROM Protocols2")
    maxid = int(c.fetchone()[0])
    newid = maxid+1
    print("Newid: %d", newid)
    for i in range(0,numitems):
        items = [newid, (i+1), flowrates[i], volumes[i], fromports[i],toports[i],datetimes[i]]
        c.execute("INSERT INTO Protocols2 VALUES (?,?,?,?,?,?,?)", items)
        print("i")

    #get current user
    curr_user = 1
    import time
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    items = [st, st, current_user_id, newid]
    print(st)
    c.execute("INSERT INTO UserProtocols3 VALUES (?,?,?,?)", items)
    print("Added")

    conn.commit()
    conn.close()

    return ('', 204)

    
@app.route('/MyProtocols')
def MyProtocols():
    global device_dict, current_user,current_user_id
    if(current_user == None):
        global devices
        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params=params)
    else:
        global device_dict
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        protocols = []
        conn = sqlite3.connect('Raspi.db')
        c = conn.cursor()
        prots = c.execute("SELECT * FROM UserProtocols3 WHERE id = ?", [current_user_id])
        for row in prots:
            name = row[0]
            time = row[1]
            protocolNum = row[3]
            protocols.append({'name':   name,
                                'time': time, 'id': protocolNum})

        params['protocols'] = protocols
        print(protocols)    
        
        

        conn.commit()
        conn.close()
        
        return render_template('MyProtocols.html', params = params)
@app.route('/Logout')
def Logout():
    global device_dict, current_user, devices,current_user_id
    valves=list(range(1,10))
    current_user = None
    current_user_id = None
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    params['username'] = current_user
    return render_template('Login.html', params = params)

@app.route('/Login')
def Login():
    print("HI")
    global device_dict, current_user, devices,current_user_id
    username = request.args["username"]
    password = request.args["password"]
    conn = sqlite3.connect('Raspi.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Users2 WHERE username = ?",[username])
    if(check_password_hash(c.fetchone()[1], password)):
        print("match")
        
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices

        c.execute("SELECT rowID FROM Users2 WHERE username = ?",[username])
        current_user_id = c.fetchone()[0]
        current_user = username
        print(current_user)
        params['username'] = current_user
        conn.commit()
        conn.close()
        return render_template('MyProtocols.html', params = params)
    else:
        print("Wrong Password")
        conn.commit()
        conn.close()

        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params = params)
    
@app.route('/Register')
def Register():
    global device_dict, current_user,devices,current_user_id
    username = request.args["username"]
    password = request.args["password"]
    confirm = request.args["confirmation"]
    email = request.args["email"]
    valves=list(range(1,10))
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    params['username'] = current_user
    if(password != confirm):
        #alert passwords dont match
        print("passwords dont match")
        return render_template('Login.html', params = params)

    conn = sqlite3.connect('Raspi.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Users2 WHERE username = ?",[username])
    if(c.fetchone() != None):
        print("Username taken")
        conn.commit()
        conn.close()
        return render_template('Login.html', params = params)
    me = User(username, password)
    hashed_password = me.pw_hash


    c.execute("INSERT INTO Users2 VALUES (?,?,?)",[username, hashed_password, email])
    valves=list(range(1,10))
    params = {}
    params['valves'] = valves
    params['devices'] = devices
    c.execute("SELECT rowID FROM Users2 WHERE username = ?",[username])
    current_user_id = c.fetchone()[0]
    current_user = username
    print("CURUSER:")
    print(current_user)
    conn.commit()
    params['username'] = current_user
    conn.close()
    return render_template('MyProtocols.html', params = params)



@app.route('/tables')
def tables():
    global devices,current_user_id
    if(current_user == None):
        params = {}
        #params['valves'] = valves
        #params['devices'] = devices
        params['username'] = current_user
        return render_template('Login.html', params=params)
    else:

        # the valve count is in the 2nd field of
        # each item in devices e.g "9dist"
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices
        params['username'] = current_user
        return render_template('tables.html')

if __name__ == '__main__':
    app.debug = True
    
    #app.run()
    app.run(host='0.0.0.0')

