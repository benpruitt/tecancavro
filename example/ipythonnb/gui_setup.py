from __future__ import print_function
from warnings import filterwarnings
filterwarnings('ignore', module='IPython.html.widgets')

from IPython.html import widgets
from IPython.display import display, clear_output, HTML

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
# devices = [('/dev/tty0', '')]
device_dict = dict(devices)

valve_control = widgets.Dropdown(options=[str(x) for x in range(1,10)])
port_control = widgets.Dropdown(options=[x[0] for x in devices])
pull_volume_control = widgets.BoundedIntText(min=0, max=1000, value=0)
push_volume_control = widgets.BoundedIntText(min=0, max=1000, value=0)
notification_area = widgets.HTML("")
def update_notification(val):
    notification_area.value = val

def call_button(button, f):
    button.disabled = True

    button.disabled = False

pull_button = widgets.Button(description="Extract")
def extract(arg):
    global device_dict
    push_button.disabled = True
    serial_port = port_control.value
    valve = int(valve_control.value)
    volume = pull_volume_control.value
    update_notification("Received extract for: %d μl from port %d on serial port %s" % (volume,
          valve, serial_port))
    if len(sp) > 0:
        device_dict[serial_port].extract(valve, volume)
    pull_button.disabled = False

pull_button.on_click(extract)
pull_button.disabled = False

push_button = widgets.Button(description="Dispense")
def dispense(arg):
    global device_dict
    push_button.disabled = True
    serial_port = port_control.value
    valve = int(valve_control.value)
    volume = push_volume_control.value
    update_notification("Received dispense for: %d μl from port %d on serial port %s" % (volume,
          valve, serial_port))
    if len(sp) > 0:
        device_dict[serial_port].dispense(valve, volume)
    push_button.disabled = False

push_button.on_click(dispense)
push_button.disabled = False


hbox0 = widgets.HBox()
sp_label = widgets.HTML("Serial Port: ")
sp_label.width = 100
hbox0.children = [sp_label, port_control]


hbox1 = widgets.HBox()
valve_label = widgets.HTML("Valve: ")
valve_label.width = 100
hbox1.children = [valve_label, valve_control]

hbox2 = widgets.HBox()
pull_button.width = 100
hbox2.children = [pull_button, pull_volume_control]

hbox3 = widgets.HBox()
push_button.width = 100
hbox3.children = [push_button, push_volume_control]

hbox4 = widgets.HBox()
notification_label = widgets.HTML("Notifications: ")
notification_label.width = 100
hbox4.children = [notification_label, notification_area]
notification_area.width = 600

vbox = widgets.VBox()
vbox.width = 600
vbox.children = [hbox0, hbox1, hbox2, hbox3, hbox4]

display(vbox)

# checkout 
# https://github.com/ipython/ipython/blob/master/IPython/html/widgets/interaction.py
# if you want to create your own interaction situation