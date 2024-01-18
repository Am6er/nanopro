import serial
import serial.tools.list_ports
import shproto
import re
import os

port_speed = 600000


def getallports():
    allports = serial.tools.list_ports.comports()
    nanoports = []
    for port in allports:
        if port.manufacturer == "FTDI" or re.search("^/dev/ttyUSB.*", port.device):
            # print("getallports: {}".format(port.device))
            nanoports.append(port)
    return nanoports


def getallportssn():
    allports = getallports()
    portssn = []
    for port in allports:
        portssn.append(port.serial_number)
    return portssn


def getallportsastext():
    allports = getallports()
    portsastext = []
    for port in allports:
        portsastext.append([port.serial_number, port.device])
        # print("getallportsastext: port: {} {} {}".format(port, port.serial_number, port.device));
    return portsastext


def getportbyserialnumber(sn):
    allports = getallports()
    for port in allports:
        if port.serial_number == sn:
            return port
    return None


def getdevicebyserialnumber(sn):
    port = getportbyserialnumber(sn)
    if port is None:
        if re.match("^/", sn) and os.path.exists(sn):
            return sn
        return None
    else:
        return getportbyserialnumber(sn).device


def connectdevice(sn=None):
    if sn is None and len(getallports()) > 0:
        nanoport = getallports()[0].device
    else:
        nanoport = getdevicebyserialnumber(sn)
    if nanoport is None:
        print("!!! Error. Could not found nano connected.")
        exit(0)
    print("port {} speed {}".format(nanoport, shproto.port.port_speed))
    # tty = serial.Serial(nanoport, baudrate=600000, bytesize=8, parity='N', stopbits=1, timeout=1)
    # tty = serial.Serial(nanoport, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=1)
    tty = serial.Serial(nanoport, baudrate=shproto.port.port_speed, bytesize=8, parity='N', stopbits=1, timeout=0.1)
    # tty = serial.Serial(nanoport, baudrate=38400, bytesize=8, parity='N', stopbits=1, timeout=0.05)
    return tty
