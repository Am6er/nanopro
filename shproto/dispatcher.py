import time

import shproto
import shproto.port

stopflag = 0
spec_stopflag = 0

histogram = [0] * 8192
command = ""

pkts01 = 0
pkts03 = 0
pkts04 = 0
total_pkts = 0

total_time = 0
cpu_load = 0
cps = 0
lost_impulses = 0

rx_arr = []


def start():
    nano = shproto.port.connectdevice()
    response = shproto.packet()
    while not shproto.dispatcher.stopflag:
        response.clear()
        shproto.dispatcher.rx_arr = []
        if len(shproto.dispatcher.command) > 1:
            print("Send comand: {}".format(command))
            if command == "-rst":
                shproto.dispatcher.histogram = [0]*8192
            tx_packet = shproto.packet()
            tx_packet.cmd = shproto.MODE_TEXT
            tx_packet.start()
            for i in range(len(command)):
                tx_packet.add(ord(command[i]))
            tx_packet.stop()
            nano.write(tx_packet.payload)
            shproto.dispatcher.command = ""
            time.sleep(0.1)
        while nano.in_waiting > 0:
            rx_byte = nano.read()
            shproto.dispatcher.rx_arr.append(rx_byte.hex())
            rx_int = int.from_bytes(rx_byte, byteorder='little')
            response.read(rx_int)
            if not response.ready:
                continue
            response.ready = 0
            shproto.dispatcher.total_pkts += 1
            if response.cmd == shproto.MODE_TEXT:
                shproto.dispatcher.pkts03 += 1
                resp_decoded = bytes(response.payload[:len(response.payload) - 2])
                try:
                    resp_decoded = resp_decoded.decode("ascii")
                except Exception:
                    print("Unknown non-text response.")
                print("<< {}".format(resp_decoded))
                break
            if response.cmd == shproto.MODE_HISTOGRAM:
                shproto.dispatcher.pkts01 += 1
                offset = response.payload[0] & 0xFF | ((response.payload[1] & 0xFF) << 8)
                count = int((response.len - 2) / 4)
                for i in range(0, count):
                    index = offset + i
                    if index < len(shproto.dispatcher.histogram):
                        value = (response.payload[i * 4 + 2]) | \
                                ((response.payload[i * 4 + 3]) << 8) | \
                                ((response.payload[i * 4 + 4]) << 16) | \
                                ((response.payload[i * 4 + 5]) << 24)
                        shproto.dispatcher.histogram[index] = value & 0x7FFFFFF
                break
            if response.cmd == shproto.MODE_STAT:
                shproto.dispatcher.pkts04 += 1
                shproto.dispatcher.total_time = (response.payload[0] & 0xFF) | \
                                                ((response.payload[1] & 0xFF) << 8) | \
                                                ((response.payload[2] & 0xFF) << 16) | \
                                                ((response.payload[3] & 0xFF) << 24)
                shproto.dispatcher.cpu_load = (response.payload[4] & 0xFF) | ((response.payload[5] & 0xFF) << 8)
                shproto.dispatcher.cps = (response.payload[6] & 0xFF) | \
                                         ((response.payload[7] & 0xFF) << 8) | \
                                         ((response.payload[8] & 0xFF) << 16) | \
                                         ((response.payload[9] & 0xFF) << 24)
                if response.len >= (15 + 2):
                    shproto.dispatcher.lost_impulses = (response.payload[10] & 0xFF) | \
                                                       ((response.payload[11] & 0xFF) << 8) | \
                                                       ((response.payload[12] & 0xFF) << 16) | \
                                                       ((response.payload[13] & 0xFF) << 24)
                break
            print("Wtf recieved: cmd:{}\r\npayload: {}".format(response.cmd, response.payload))
        response.clear()
        time.sleep(0.1)
    nano.close()


def stop():
    shproto.dispatcher.stopflag = 1


def spec_stop():
    shproto.dispatcher.spec_stopflag = 1


def process_03(_command: str):
    shproto.dispatcher.command = _command


def process_01(filename):
    print("Start writing spectrum to file: {}".format(filename))
    fd = open(filename, "w")
    timer = 0
    while (not shproto.dispatcher.stopflag) or (not shproto.dispatcher.spec_stopflag):
        time.sleep(1)
        timer = timer + 1
        if timer == 5:
            fd.seek(0)
            for i in range(0, 1300):
                fd.writelines("{}, {}\r\n".format(i + 1, shproto.dispatcher.histogram[i]))
            fd.flush()
            fd.truncate()
            timer = 0
    fd.close()
    print("Stop collecting spectrum")
