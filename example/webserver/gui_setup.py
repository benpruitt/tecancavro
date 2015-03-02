from __future__ import print_function
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
devices = [('/dev/tty0', '')]
device_dict = dict(devices)

valve_control = widgets.Dropdown(options=[str(x) for x in range(1,10)])
port_control = widgets.Dropdown(options=[x[0] for x in devices])
pull_volume_control = widgets.BoundedIntText(min=0, max=1000, value=0)
push_volume_control = widgets.BoundedIntText(min=0, max=1000, value=0)
notification_area = widgets.Text("")
def update_notification(val):
    notification_area.value = val

def call_button(button, f):
    button.disabled = True

    button.disabled = False

pull_button = widgets.Button(description="Extract")
def extract():
    global device_dict
    push_button.disabled = True
    serial_port = port_control.value
    port = valve_control.value
    volume = pull_volume_control.value
    update_notification("Received extract for: %d ul from port %d on serial port %s" % (volume,
          port, serial_port))
    if len(sp) > 0:
        device_dict[serial_port].extract(port, volume)
    pull_button.disabled = False

pull_button.on_click(extract)
pull_button.disabled = False

push_button = widgets.Button(description="Dispense")
def dispense():
    global device_dict
    push_button.disabled = True
    serial_port = port_control.value
    port = valve_control.value
    volume = push_volume_control.value
    update_notification("Received dispense for: %d ul from port %d on serial port %s" % (volume,
          port, serial_port))
    if len(sp) > 0:
        device_dict[serial_port].dispense(port, volume)
    push_button.disabled = False

push_button.on_click(lambda x: update_notification("poop")) #dispense
push_button.disabled = False


hbox0 = widgets.HBox()
hbox0.children = [widgets.Text("Serial Port:"), port_control]

hbox1 = widgets.HBox()
hbox1.children = [widgets.Text("Valve:"), valve_control]

hbox2 = widgets.HBox()
hbox2.children = [pull_button, pull_volume_control]

hbox3 = widgets.HBox()
hbox3.children = [push_button, push_volume_control]

hbox4 = widgets.HBox()
hbox4.children = [widgets.Text("Notifications: "), notification_area]

vbox = widgets.VBox()
vbox.children = [hbox0, hbox1, hbox2, hbox3, hbox4]

display(vbox)

# checkout 
# https://github.com/ipython/ipython/blob/master/IPython/html/widgets/interaction.py
# if you want to create your own interaction situation