import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from struct import *
import binascii
import re

import shproto
import shproto.port

stopflag = 0
stopflag_lock = threading.Lock()
spec_stopflag = 0
spec_stopflag_lock = threading.Lock()

histogram = [0] * 8192
histogram_lock = threading.Lock()

command = ""
command_lock = threading.Lock()

pkts01 = 0
pkts03 = 0
pkts04 = 0
total_pkts = 0
dropped = 0

total_time = 0
cpu_load = 0
cps = 0
cps_lock = threading.Lock()
lost_impulses = 0
total_pulse_width = 0
serial_number = ""
calibration = [0., 1., 0., 0., 0.]
inf_str = ''


def start(sn=None):
    pulse_file_opened = 2
    # READ_BUFFER = 1
    # READ_BUFFER = 2048
    READ_BUFFER = 2048
    # READ_BUFFER = 8192
    shproto.dispatcher.clear()
    with shproto.dispatcher.stopflag_lock:
        shproto.dispatcher.stopflag = 0
    nano = shproto.port.connectdevice(sn)
    response = shproto.packet()
    while not shproto.dispatcher.stopflag:
        if len(shproto.dispatcher.command) > 1:
            print("Send command: {}".format(command))
            if command == "-rst":
                shproto.dispatcher.clear()
            tx_packet = shproto.packet()
            tx_packet.cmd = shproto.MODE_TEXT
            tx_packet.start()
            for i in range(len(command)):
                tx_packet.add(ord(command[i]))
            tx_packet.stop()
            nano.write(tx_packet.payload)
            with shproto.dispatcher.command_lock:
                shproto.dispatcher.command = ""
        if nano.in_waiting == 0:
            time.sleep(0.05)
            continue
        READ_BUFFER = max(nano.in_waiting, READ_BUFFER)
        rx_byte_arr = nano.read(size=READ_BUFFER)
        # print("rx_byte_arr len = {}/{}".format(len(rx_byte_arr),READ_BUFFER))
        for rx_byte in rx_byte_arr:
            response.read(rx_byte)
            if response.dropped:
                shproto.dispatcher.dropped += 1
                shproto.dispatcher.total_pkts += 1
            if not response.ready:
                continue
            shproto.dispatcher.total_pkts += 1
            if response.cmd == shproto.MODE_TEXT:
                print("<< got text")
                shproto.dispatcher.pkts03 += 1
                resp_decoded = bytes(response.payload[:len(response.payload) - 2])
                resp_lines = []
                try:
                    resp_decoded = resp_decoded.decode("ascii")
                    resp_lines = resp_decoded.splitlines()
                    if re.search('^VERSION', resp_decoded):
                        shproto.dispatcher.inf_str = resp_decoded
                        shproto.dispatcher.inf_str = re.sub(r'\[[^]]*\]', '...', shproto.dispatcher.inf_str, count = 2)
                except UnicodeDecodeError:
                    print("Unknown non-text response.")
                print("<< {}".format(resp_decoded))
                if len(resp_lines) == 40:
                    shproto.dispatcher.serial_number = resp_lines[39];
                    print("got detector serial num: {}".format(shproto.dispatcher.serial_number))
                    b_str =  ''
                    for b in resp_lines[0:10]:
                        b_str += b
                    #crc = hex(binascii.crc32(bytearray(b_str, 'ascii')) % 2**32)
                    crc = binascii.crc32(bytearray(b_str, 'ascii')) % 2**32

                    if (crc == int(resp_lines[10],16)):
                        shproto.dispatcher.calibration[0] = unpack('d', int((resp_lines[0] + resp_lines[1]),16).to_bytes(8, 'little'))[0]
                        shproto.dispatcher.calibration[1] = unpack('d', int((resp_lines[2] + resp_lines[3]),16).to_bytes(8, 'little'))[0]
                        shproto.dispatcher.calibration[2] = unpack('d', int((resp_lines[4] + resp_lines[5]),16).to_bytes(8, 'little'))[0]
                        shproto.dispatcher.calibration[3] = unpack('d', int((resp_lines[6] + resp_lines[7]),16).to_bytes(8, 'little'))[0]
                        shproto.dispatcher.calibration[4] = unpack('d', int((resp_lines[8] + resp_lines[9]),16).to_bytes(8, 'little'))[0]
                        print("got calibration: {}".format(shproto.dispatcher.calibration)
                            )
                    #
                    else:
                        print("wrong crc for calibration values got: {:08x} expected: {:08x}".format(int(resp_lines[10],16), crc))
                    #
                    #
	
                response.clear()
            elif response.cmd == shproto.MODE_HISTOGRAM:
                #print("<< got histogram")
                shproto.dispatcher.pkts01 += 1
                offset = response.payload[0] & 0xFF | ((response.payload[1] & 0xFF) << 8)
                count = int((response.len - 2) / 4)
                ## print("histogram count: {} offset: {}".format(count, offset))
                with shproto.dispatcher.histogram_lock:
                    for i in range(0, count):
                        index = offset + i
                        if index < len(shproto.dispatcher.histogram):
                            value = (response.payload[i * 4 + 2]) | \
                                    ((response.payload[i * 4 + 3]) << 8) | \
                                    ((response.payload[i * 4 + 4]) << 16) | \
                                    ((response.payload[i * 4 + 5]) << 24)
                            shproto.dispatcher.histogram[index] = value & 0x7FFFFFF
                response.clear()
            elif response.cmd == shproto.MODE_PULSE:
                if pulse_file_opened != 1:
                    # fd_pulses = open("/home/bag/nanopro/pulses.csv", "w+")
                    fd_pulses = open("/tmp/pulses.csv", "w+")
                    # print("file /home/bag/nanopro/pulses.csv open return", fd_pulses)
                    print("file /tmp/pulses.csv open return", fd_pulses)
                    pulse_file_opened = 1

                #print("<< got pulse", fd_pulses)
                shproto.dispatcher.pkts01 += 1
                offset = response.payload[0] & 0xFF | ((response.payload[1] & 0xFF) << 8)
                count = int((response.len - 2) / 2)
                pulse = []
                for i in range(0, count):
                    index = offset + i
                    if index < len(shproto.dispatcher.histogram):
                        value = (response.payload[i * 2 + 2]) | \
                                ((response.payload[i * 2 + 3]) << 8)
                        pulse = pulse + [(value & 0x7FFFFFF)]
                    fd_pulses.writelines("{:d} ".format(value & 0x7FFFFFF))
                fd_pulses.writelines("\n")
                fd_pulses.flush()
                # print("len: ", count, "shape: ", pulse)
                response.clear()
            elif response.cmd == shproto.MODE_STAT:
                # print("<< got stat")
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
                if response.len >= (11 + 2):
                    shproto.dispatcher.lost_impulses = (response.payload[10] & 0xFF) | \
                                                       ((response.payload[11] & 0xFF) << 8) | \
                                                       ((response.payload[12] & 0xFF) << 16) | \
                                                       ((response.payload[13] & 0xFF) << 24)
                if response.len >= (15 + 2):
                    shproto.dispatcher.total_pulse_width = (response.payload[14] & 0xFF) | \
                                                       ((response.payload[15] & 0xFF) << 8) | \
                                                       ((response.payload[16] & 0xFF) << 16) | \
                                                       ((response.payload[17] & 0xFF) << 24)
                #print("stat elapsed: {} cps: {} total: {} lost: {} cpu: {} total_pulse_width: {}".format(
                #    shproto.dispatcher.total_time, shproto.dispatcher.cps, shproto.dispatcher.total_pkts,
                #    shproto.dispatcher.lost_impulses, shproto.dispatcher.cpu_load, shproto.dispatcher.total_pulse_width))
                response.clear()
            else:
                print("Wtf received: cmd:{}\r\npayload: {}".format(response.cmd, response.payload))
                response.clear()
    nano.close()


def process_01(filename):
    timer = 0
    print("Start writing spectrum to file: {}".format(filename))
    with shproto.dispatcher.spec_stopflag_lock:
        shproto.dispatcher.spec_stopflag = 0
    while not (shproto.dispatcher.spec_stopflag or shproto.dispatcher.stopflag):
        timer += 1
        time.sleep(1)
        if timer == 5:
            timer = 0
            spec_pulses_total = sum(shproto.dispatcher.histogram)
            spec_pulses_total_cps = 0
            spec_timestamp = datetime.now(timezone.utc) - + timedelta(seconds=shproto.dispatcher.total_time)
            if shproto.dispatcher.total_time > 0:
                spec_pulses_total_cps = float(spec_pulses_total) / float(shproto.dispatcher.total_time)
            print("elapsed: {} cps: {}/{:.2f} total_pkts: {} drop_pkts: {} lostImp: {} cpu: {}".format(
               shproto.dispatcher.total_time, shproto.dispatcher.cps, spec_pulses_total_cps,
               shproto.dispatcher.total_pkts, shproto.dispatcher.dropped,
               shproto.dispatcher.lost_impulses, shproto.dispatcher.cpu_load))
            with open(filename, "w") as fd:
                fd.seek(0)

                # 1MHz fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(0, 2.98307E-06, 0.378484, -9.78218))
                # fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(0, 1.364E-06, 0.386, -12))	# 1MHz r7 f7 n14 
                # fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(0, 2.127E-06, 0.3827, -8.5))	# 1MHz r7 f7 n14 NoTHR
                fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(
                    shproto.dispatcher.calibration[3],
                    shproto.dispatcher.calibration[2],
                    shproto.dispatcher.calibration[1],
                    shproto.dispatcher.calibration[0]))
                # 1.2MHz fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(0, 2.21E-06, 0.316, -2))
                # 1.2MHz fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(0, 1.61E-06, 0.3185, -7.64))
                # 1.2MHz fd.writelines("calibcoeff : a={} b={} c={} d={}\n".format(0, 1.8E-06, 0.3185, -7.64))
                fd.writelines(
                    "remark, elapsed: {:d}H:{:02d}m/{:5d}s/{:.2f}m cps: {:7.2f} total_pulses: {} total_pkts: {} drop_pkts: {} lostImp: {}\n".format(
                        int(shproto.dispatcher.total_time/3600), int((shproto.dispatcher.total_time%3600)/60),
                        shproto.dispatcher.total_time, 
                        shproto.dispatcher.total_time/60.,
                        spec_pulses_total_cps, spec_pulses_total, shproto.dispatcher.total_pkts,
                        shproto.dispatcher.dropped, shproto.dispatcher.lost_impulses
                        ))
                if shproto.dispatcher.inf_str != "":
                    fd.writelines("remark, inf: {}".format(shproto.dispatcher.inf_str))
                fd.writelines("livetime, {}\n".format(shproto.dispatcher.total_time))
                fd.writelines("realtime, {}\n".format(shproto.dispatcher.total_time))
                fd.writelines("detectorname,nano15-8k-{}\nSerialNumber,nano15-8k-{}\n".format(
                    shproto.dispatcher.serial_number,shproto.dispatcher.serial_number))
                fd.writelines("starttime, {}\n".format(spec_timestamp.strftime("%Y-%m-%dT%H:%M:%S+00:00")))
                fd.writelines("ch,data\n")

                for i in range(0, 8192):
                    fd.writelines("{}, {}\n".format(i + 1, shproto.dispatcher.histogram[i]))
                fd.flush()
                fd.truncate()
    print("Stop collecting spectrum")


def stop():
    with shproto.dispatcher.stopflag_lock:
        shproto.dispatcher.stopflag = 1


def spec_stop():
    with shproto.dispatcher.spec_stopflag_lock:
        shproto.dispatcher.spec_stopflag = 1


def process_03(_command):
    with shproto.dispatcher.command_lock:
        shproto.dispatcher.command = _command


def clear():
    with shproto.dispatcher.histogram_lock:
        shproto.dispatcher.histogram = [0] * 8192
        shproto.dispatcher.pkts01 = 0
        shproto.dispatcher.pkts03 = 0
        shproto.dispatcher.pkts04 = 0
        shproto.dispatcher.total_pkts = 0
        shproto.dispatcher.cpu_load = 0
        shproto.dispatcher.cps = 0
        shproto.dispatcher.total_time = 0
        shproto.dispatcher.lost_impulses = 0
        shproto.dispatcher.total_pulse_width = 0
        shproto.dispatcher.dropped = 0
