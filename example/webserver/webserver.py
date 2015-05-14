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
import time
import numpy as np
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from pytz import timezone
from threading import Thread
from time import sleep
import RPi.GPIO as GPIO  


x = 1;

# CONSTANTS 
PUMP_VOLUME_UL = 5000.0
EXTRACT_SPEED = 22
SPEED_CODES_STROKE = {
                        0: 1.25, 1: 1.3, 2: 1.39, 3: 1.52, 4: 1.71, 5: 1.97,
                        6: 2.37, 7: 2.77, 8: 3.03, 9: 3.36, 10: 3.77, 11: 4.3,
                        12: 5.0, 13: 6.0, 14: 7.5, 15: 10.0, 16: 15.0, 17: 30.0,
                        18: 31.58, 19: 33.33, 20: 35.29, 21: 37.50, 22: 40.0, 
                        23: 42.86, 24: 46.15, 25: 50.0, 26: 54.55, 17: 60.0, 
                        28: 66.67, 29: 75.0, 30: 85.71, 31: 100.0, 32: 120.0, 
                        33: 150.0, 34: 200.0, 35: 300.0, 36: 333.33,
                        37: 375.0, 38: 428.57, 39: 500.0, 40: 600.0
                        }


#Prepare Flask
app = Flask(__name__)

#add celery constants
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


def threaded_function(arg):
    global device_dict
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(14, GPIO.IN) 
    GPIO.wait_for_edge(14, GPIO.BOTH)  
    print ("Change Detected")
    device_dict[sp].resetChain(on_execute=True, minimal_reset=False)
    device_dict[sp].extract(1, 5000, speed = 14, execute = False)
    device_dict[sp].dispense(1, 5000, speed = 14, execute = False)
    



# Class for user 
class User(object):
    def __init__(self, username, password):
        self.username = username
        self.set_password(password)

    def set_password(self, password):
        self.pw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pw_hash, password)     


#Currently logged in
current_user = None
current_user_id = None

#Currently not paused
paused = False


Bootstrap(app)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True




#Import tecan library
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
            `rate_ul_s` : rate in microliters/second

        """
        #Determine the targeted second/stroke time
        target_sec_per_stroke = PUMP_VOLUME_UL / float(rate_ul_s)

        #Find speed code that matches target_sec_per_stroke as close as possible
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


#Go through each device, initialize and set speed
devices = getSerialPumps()
device_dict = dict(devices)
for item in devices:
    device_dict[item[0]].init()
    device_dict[item[0]].setSpeed(25)


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
    '''
        Prepares the template for Simple_Commands
        Attatches:
            -Number of valves in the pump
            -Connected devices
            -Username of current user

        Sends user to login if no one is currently logged in
    '''
    global device_dict, current_user, devices,current_user_id

    #Parameters to pass into template
    params = {}
    params['valves'] = list(range(1,10))
    params['devices'] = devices
    params['username'] = current_user

    if(current_user == None):
        return render_template('Login.html', params = params)
    else:
        return render_template('Simple_Commands.html', params = params)

@app.route('/AdvancedProtocol')
def AdvancedProtocol():
    '''
        Prepares the template for creating an AdvancedProtocol
        Attatches:
            -Number of valves in the pump
            -Connected devices
            -Username of current user
            -len 
                * 0 indictes we are not loading an old protocol
                * 1 indicates we are loading an old protocol
            -protocols is the list of information to be added 
                when loading an old protocol

        Sends user to login if no one is currently logged in
    '''
    global device_dict, current_user, devices, current_user_id

    #Parameters to pass into template
    params = {}
    params['valves'] = list(range(1,10))
    params['devices'] = devices
    params['username'] = current_user

    #Send user to login if not logged in
    if(current_user == None):
        return render_template('Login.html', params=params)
    else:

        #Check to see if we are loading an old protocol
        try: 
            protocol_id = request.args['id']
            old_protocol = True
        except:  #No id, not an old protocol
            old_protocol = False

        #New protocol can just render the page
        if(not old_protocol):
            params['len'] = 0
            return render_template('AdvancedProtocol.html', params=params)
        else:
            params['len'] = 1

            #Connect to sql database
            conn = sqlite3.connect('Raspi.db')
            c = conn.cursor()
            protocolsnew = []

            #Grab selected protocol from databased
            prots = c.execute("SELECT * FROM Protocols WHERE id = ?", [protocol_id])
            
            #Add protocol items to be loaded
            for row in prots:
                number = str(row[1])
                rate = row[2]
                vol = row[3]
                fromport = row[4]
                toport = row[5]
                hours = row[6]
                minutes = row[7]
                seconds = row[8]
                cycle = row[9]
                numrepeats = row[10]
                protocolsnew.append({"num": number,
                                     "rate": rate,
                                     "vol": vol, 
                                     "fromport": fromport, 
                                     "toport": toport,
                                     "hours": hours,
                                     "minutes": minutes,
                                     "seconds": seconds,
                                     "cycles": cycle,
                                     "numrepeats": numrepeats
                                     })

            params['protocols'] = protocolsnew
            
            
            #close db
            conn.commit()
            conn.close()
            return render_template('AdvancedProtocol.html', params=params)

@app.route('/MyProtocols')
def MyProtocols():
    '''
        Prepares the template for viewing Saved Protocols
        Attatches:
            -Number of valves in the pump
            -Connected devices
            -Username of current user
            -

        Sends user to login if no one is currently logged in
    '''
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
        prots = c.execute("SELECT * FROM UserProtocols WHERE user = ?", [current_user_id])
        for row in prots:
            name = row[0]
            time = row[1]
            protocolNum = row[3]
            protocols.append({'name':   name,
                                'time': time, 'id': protocolNum})

        params['protocols'] = protocols
        
        

        conn.commit()
        conn.close()
        
        return render_template('MyProtocols.html', params = params)     


@app.route('/extract')
def extract_call():
    global device_dict, current_user,current_user_id
    volume = int(request.args['volume'])
    port = int(request.args['port'])
    sp = request.args['serial_port']
    rate = int(request.args['rate'])
    if(rate != 0 and len(sp) > 0):
        newSpeed = _rateToSpeed(rate)

        


    willex = int(request.args['exec'])
    if(willex == 0):
        executing = False
    else:
        executing = True
        
    print("Received extract for: %d ul from port %d on serial port %s" % (volume,
          port, sp))
    if len(sp) > 0:
        device_dict[sp].resetChain(on_execute=True, minimal_reset=False)
        device_dict[sp].extract(port, volume, speed = newSpeed, execute = executing)
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
        

    willex = int(request.args['exec'])
    if(willex == 0):
        executing = False
    else:
        executing = True
        
    print("Received dispense for: %d ul from port %d on serial port %s" % (volume,
          port, sp))
    if len(sp) > 0:
        device_dict[sp].resetChain(on_execute=True, minimal_reset=False)
        device_dict[sp].dispense(port, volume, speed = newSpeed, execute = executing)
    return ('', 204)
@app.route('/reset')
def reset():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
    if len(sp) > 0:
        device_dict[sp].terminateExec()
        device_dict[sp].resetChain()
        device_dict[sp].init()
    return ('', 204)

@app.route('/pause')
def pause():
    global device_dict, current_user,current_user_id, paused
    paused = True
    sp = request.args['serial_port']
    if len(sp) > 0:
        device_dict[sp].terminateExec()
    return ('', 204)

@app.route('/resume')
def resume():
    global device_dict, current_user,current_user_id, paused
    sp = request.args['serial_port']
    
    if len(sp) > 0 and paused:
        device_dict[sp].executeChain()
    paused = False
    return ('', 204)

@app.route('/execute')
def execute_chain():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
    if len(sp) > 0:
        device_dict[sp].executeChain()
    return ('', 204)
@app.route('/halt')
def halt():
    global device_dict, current_user,current_user_id
    sp = request.args['serial_port']
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
    flowrates =  json.loads(request.args['flowrates'])
    volumes =  json.loads(request.args['volumes'])
    hours =  json.loads(request.args['hours'])
    minutes =  json.loads(request.args['minutes'])
    seconds =  json.loads(request.args['seconds'])
    cycles =  json.loads(request.args['cycles'])
    repeats =  json.loads(request.args['repeats'])
    saveProtocol(True, sp, numitems, fromports, toports, flowrates, volumes, hours, minutes, seconds, cycles, repeats)
    
    # loop_array = np.zeros(numitems)
    # break_array = np.zeros(numitems)
    # loops_to_break = np.zeros(numitems)
    # loops_lens = np.zeros(numitems)
    # break_lens = np.zeros(numitems)
    # for i in range(0, numitems):
    #     time_len = int(seconds[i]) + 60*int(minutes[i]) + 3600*int(hours[i])
    #     if(volumes[i] == 0 and time_len > 5*60):
    #         break_array[i] = 1
    #     if(cycles[i] == "Start"):
    #         loop_array[i] = 1
    #     if(cycles[i] == "End"):
    #         loop_array[i] = 2
    # last_start = -1
    # first_end = -1
    # breakcount = -1
    # while(True):
    #     for i in range(0, numitems):
    #         if(loop_array[i] == 1):
    #             last_start = i;
    #             breakcount = 0;
    #         if(loop_array[i] == 2):
    #             loops_lens[last_start] = i - last_start + 1
    #             if(breakcount > 0):
    #                 loops_to_break[last_start] = 1
    #             else:
    #                 loop_array[last_start] = 0
    #                 loop_array[i] = 0;
    #             break;
    #         if(break_array[i] == 1):
    #             breakcount = breakcount + 1

    #     if(last_start == -1):
    #         break;
    # start = 0
    # for i in range(0, numitems):
    #     if(break_array[i] == 1):
    #         break_lens[start] = i - start + 1

    # for i in range(0, numitems):
    #     if(cycles[i] == "Start"):
            
    #     else if(cycles[i] == "End"):
            
    #     else



    reset()
    device_dict[sp].resetChain(on_execute=True, minimal_reset=False)
    for i in range(0,numitems):
        createTask(int(fromports[i]), int(toports[i]), float(flowrates[i]), float(volumes[i]), int(hours[i]), int(minutes[i]),int(seconds[i]), cycles[i], repeats[i], sp)
    time_to_exec = device_dict[sp].executeChain()
    print("Exec time")
    print(time_to_exec)
    return ('', 204)
    

def createTask(from_port_id, to_port_id, flowrate_ul_s, volume_ul, hour_num, min_num, sec_num, cycles, repeat_num, sp):
    global device_dict, current_user,current_user_id
    if(len(sp) > 0):
        if(cycles != "End"):
            if(cycles == "Start"):
                device_dict[sp].markRepeatStart()
            time_len = sec_num + 60*min_num + 3600*hour_num
            if(flowrate_ul_s * time_len != volume_ul):
                print("ERROR, incorrect conversions")
                print(flowrate_ul_s * time_len)
            speed_to_use = 0
            if(flowrate_ul_s == 0 and volume_ul == 0):
                delaytime = time_len*1000
                MAX_DELAY = 30000
                num_pause_cycles = int(delaytime/MAX_DELAY)
                extra_delay = int(delaytime) % MAX_DELAY
                if(num_pause_cycles > 0):
                    device_dict[sp].markRepeatStart()
                    device_dict[sp].delayExec(MAX_DELAY)
                    device_dict[sp].repeatCmdSeq(num_pause_cycles)
                if(extra_delay > 0):
                    device_dict[sp].delayExec(extra_delay)
            elif(flowrate_ul_s != 0):
                speed_to_use = _rateToSpeed(flowrate_ul_s)
                actual_rate_ul_s = PUMP_VOLUME_UL / float(SPEED_CODES_STROKE[speed_to_use])
                target_time_s = volume_ul / flowrate_ul_s
                if(target_time_s != time_len):
                    print("CONVERSION ERROR")
                actual_time_s = volume_ul / actual_rate_ul_s
                if(actual_time_s == target_time_s):
                    numberrepeats = int(volume_ul/PUMP_VOLUME_UL)
                    extra = int(volume_ul) % PUMP_VOLUME_UL
                    if(numberrepeats > 0):
                        device_dict[sp].markRepeatStart()
                        device_dict[sp].extract(int(from_port_id), int(PUMP_VOLUME_UL), speed = EXTRACT_SPEED)
                        device_dict[sp].dispense(int(to_port_id), int(PUMP_VOLUME_UL), speed = speed_to_use)
                        device_dict[sp].repeatCmdSeq(numberrepeats)
                    if(extra > 0):
                        device_dict[sp].extract(int(from_port_id), int(extra), speed = EXTRACT_SPEED)
                        device_dict[sp].dispense(int(to_port_id), int(extra), speed = speed_to_use)
                    
                else:
                    #NEED TO CHANGE TO MAKE ACTUAL

                    BASEDIVIDE = 10
                                   
                    print("NOT exact")
                    volume_remaining = volume_ul
                    if(actual_time_s > target_time_s):
                        if(speed_to_use == 0):
                            print("Cant go faster")
                        else:
                            speed_to_use = speed_to_use - 1

                    actual_rate_ul_s = PUMP_VOLUME_UL / float(SPEED_CODES_STROKE[speed_to_use])
                    actual_time_s = volume_ul / actual_rate_ul_s

                    time_to_make_up = target_time_s - actual_time_s
                    assert(time_to_make_up > 0)
                    print(time_to_make_up)

                    numloop = float(volume_ul) / float(PUMP_VOLUME_UL)

                    break_time_per_loop = float(time_to_make_up) / numloop
                    
                    while volume_remaining > 0:
                        if volume_remaining >= PUMP_VOLUME_UL:
                            device_dict[sp].extract(int(from_port_id), int(PUMP_VOLUME_UL), speed = EXTRACT_SPEED)
                            brk = int(5 * break_time_per_loop)
                            print("brk")
                            print(brk)
                            if(brk > 0):
                                device_dict[sp].markRepeatStart()
                                device_dict[sp].dispense(int(to_port_id), int(25), speed = speed_to_use)
                                MAX_DELAY = 30000
                                num_brk_cycles = int(brk/MAX_DELAY)
                                extra_delay = int(brk) % MAX_DELAY
                                if(num_brk_cycles > 0):
                                    device_dict[sp].markRepeatStart()
                                    device_dict[sp].delayExec(MAX_DELAY)
                                    device_dict[sp].repeatCmdSeq(num_pause_cycles)
                                if(extra_delay > 0):
                                    device_dict[sp].delayExec(extra_delay)
                                device_dict[sp].repeatCmdSeq(int(PUMP_VOLUME_UL/25))
                            else:
                                device_dict[sp].dispense(int(to_port_id), int(PUMP_VOLUME_UL), speed = speed_to_use)
                            volume_remaining = volume_remaining - PUMP_VOLUME_UL
                        else:
                            device_dict[sp].extract(int(from_port_id), int(volume_remaining), speed = EXTRACT_SPEED)
                            num_tens = int(volume_remaining / 10)
                            rem = int(volume_remaining) % 10


                            brk = int(1000 * break_time_per_loop * (volume_remaining / PUMP_VOLUME_UL) / num_tens)
                            print("brk")
                            print(brk)
                            if(brk > 0):
                                device_dict[sp].markRepeatStart()
                                device_dict[sp].dispense(int(to_port_id), int(10), speed = speed_to_use)
                                MAX_DELAY = 30000
                                num_brk_cycles = int(brk / MAX_DELAY)
                                extra_delay = int(brk) % MAX_DELAY
                                if(num_brk_cycles > 0):
                                    device_dict[sp].markRepeatStart()
                                    device_dict[sp].delayExec(MAX_DELAY)
                                    device_dict[sp].repeatCmdSeq(num_pause_cycles)
                                if(extra_delay > 0):
                                    device_dict[sp].delayExec(extra_delay)
                                device_dict[sp].repeatCmdSeq(num_tens)
                                device_dict[sp].dispense(int(to_port_id), int(rem), speed = speed_to_use)
                            else:
                                device_dict[sp].dispense(int(to_port_id), int(volume_remaining), speed = speed_to_use)

                            volume_remaining = 0

                        
            else:
                return "ERROR"   
        else:
            device_dict[sp].repeatCmdSeq(int(repeat_num))


@app.route('/saveProtocol')
def saveProtocol(local_call = False, sp=None, numitems = None, fromports = None, toports = None, flowrates = None, volumes = None, hours = None, minutes = None, seconds = None, cycles = None, repeats = None):
    global device_dict, current_user,current_user_id
    if(not local_call):
        sp = request.args['serial_port']
        numitems = int(request.args['numitems'])
        fromports =  json.loads(request.args['fromports'])
        toports =  json.loads(request.args['toports'])
        flowrates =  json.loads(request.args['flowrates'])
        volumes =  json.loads(request.args['volumes'])
        hours =  json.loads(request.args['hours'])
        minutes =  json.loads(request.args['minutes'])
        seconds =  json.loads(request.args['seconds'])
        cycles =  json.loads(request.args['cycles'])
        repeats =  json.loads(request.args['repeats'])

    conn = sqlite3.connect('Raspi.db')
    c = conn.cursor()
    #change to make use unused numbers not max
    c.execute("SELECT MAX(id) FROM Protocols")
    maxid = int(c.fetchone()[0])
    newid = maxid+1
    for i in range(0,numitems):
        items = [newid, (i+1), float(flowrates[i]), float(volumes[i]), int(fromports[i]),int(toports[i]),int(hours[i]),int(minutes[i]), int(seconds[i]),cycles[i],int(repeats[i])]
        c.execute("INSERT INTO Protocols VALUES (?,?,?,?,?,?,?,?,?,?,?)", items)

    
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    items = [st, st, current_user_id, newid]
    c.execute("INSERT INTO UserProtocols VALUES (?,?,?,?)", items)

    conn.commit()
    conn.close()

    return ('', 204)

    

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
    global device_dict, current_user, devices,current_user_id
    username = request.args["username"]
    password = request.args["password"]
    conn = sqlite3.connect('Raspi.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Users2 WHERE username = ?",[username])
    if(check_password_hash(c.fetchone()[1], password)):
        
        valves=list(range(1,10))
        params = {}
        params['valves'] = valves
        params['devices'] = devices

        c.execute("SELECT rowID FROM Users2 WHERE username = ?",[username])
        current_user_id = c.fetchone()[0]
        current_user = username
        params['username'] = current_user
        conn.commit()
        conn.close()
        return MyProtocols()
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
    conn.commit()
    params['username'] = current_user
    conn.close()
    return render_template('MyProtocols.html', params = params)

if __name__ == '__main__':
    app.debug = False
    #app.run()
    thread = Thread(target = threaded_function, args = (10, ))
    thread.start()
    #thread.join()
    print("hi")
    app.run(host='0.0.0.0')
    GPIO.cleanup()         
    print("bye")



