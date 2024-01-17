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

max_pulses_buf = 10000
pulses_buf = []
pulse_file_opened = 0
pulses_debug_count = 0

start_timestamp = datetime.now(timezone.utc)

def start(sn=None):
    shproto.dispatcher.pulse_file_opened = 2
    # READ_BUFFER = 1
    READ_BUFFER = 4096
    # READ_BUFFER = 2048
    # READ_BUFFER = 8192
    # READ_BUFFER = 65536
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
                if (not re.search('^mi.*index.*', resp_decoded)):
                    # mi 5423 s 2 index 1388 integ 2900 mx 457 th 14 count 16 proc_case 3 from 5416 to 5432 pm 1 ):
                    print("<< got text")
                    print("<< {}".format(resp_decoded))
                    # print("pulse: {}".format(resp_decoded))
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
                # offset = response.payload[0] & 0xFF | ((response.payload[1] & 0xFF) << 8)
                offset = unpack("<H", bytes(response.payload[0:2]))[0]
                count = int((response.len - 2) / 4)
                ## print("histogram count: {} offset: {}".format(count, offset))
                with shproto.dispatcher.histogram_lock:
                    if (offset <= 8192 and offset+count <= 8192):
                        format_unpack_str = "<{}I".format(count)
                        
                        shproto.dispatcher.histogram[offset:offset+count] = list(unpack(format_unpack_str, bytes(response.payload[2:count*4+2])))
                    else:
                        print("histogram index is out of range: {} - {} c:{}".format(offset, offset+count, offset+count))
                response.clear()
            elif response.cmd == shproto.MODE_PULSE:
                #print("<< got pulse", fd_pulses)
                shproto.dispatcher.pkts01 += 1
                # offset = response.payload[0] & 0xFF | ((response.payload[1] & 0xFF) << 8)
                offset = unpack("<H", bytes(response.payload[0:2]))[0]
                count = int((response.len - 2) / 2)
                format_unpack_str = "<{}H".format(count)
                format_print_str = "{}{:d}:d{}".format("{", count, "}")
                pulse = list(unpack(format_unpack_str, bytes(response.payload[2:count*2+2])))
                # str3 = ' '.join("{:d}".format(p) for p in  pulse1)
                # print("format: {} {} pulse unpack: {}".format(format_unpack_str, format_print_str, str3))
                # for i in range(0, count):
                #     index = offset + i
                #     if index < len(shproto.dispatcher.histogram):
                #         value = (response.payload[i * 2 + 2]) | \
                #                 ((response.payload[i * 2 + 3]) << 8)
                #         pulse = pulse + [(value & 0x7FFFFFF)]
                #     fd_pulses.writelines("{:d} ".format(value & 0x7FFFFFF))
                if len(shproto.dispatcher.pulses_buf) < max_pulses_buf:
                    with shproto.dispatcher.histogram_lock:
                        shproto.dispatcher.pulses_buf.append(pulse)
                # print("len: ", count, "shape: ", pulse)
                response.clear()
            elif response.cmd == shproto.MODE_STAT:
                # print("<< got stat")
                shproto.dispatcher.pkts04 += 1
                shproto.dispatcher.total_time = unpack("<I", bytes(response.payload[0:4]))[0]
                shproto.dispatcher.cpu_load = unpack("<H", bytes(response.payload[4:6]))[0]
                shproto.dispatcher.cps = unpack("<I", bytes(response.payload[6:10]))[0]
                if response.len >= (11 + 2):
                    shproto.dispatcher.lost_impulses = unpack("<I", bytes(response.payload[10:14]))[0]
                if response.len >= (15 + 2):
                    shproto.dispatcher.total_pulse_width = unpack("<I", bytes(response.payload[14:18]))[0]
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
            with shproto.dispatcher.histogram_lock:
                histogram = shproto.dispatcher.histogram
            spec_pulses_total = sum(histogram)
            spec_pulses_total_cps = 0
            spec_timestamp = datetime.now(timezone.utc) - timedelta(seconds=shproto.dispatcher.total_time)
            if shproto.dispatcher.total_time > 0:
                spec_pulses_total_cps = float(spec_pulses_total) / float(shproto.dispatcher.total_time)
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
                    "remark, elapsed: {:d}H:{:02d}m/{:d}s/{:.2f}m cps: {:7.2f} total_pulses: {} total_pkts: {} drop_pkts: {} lostImp: {}\n".format(
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
                if len(histogram) > 8192:
                    print("histogram len too long {}".format(len(histogram)))
                for i in range(0, len(histogram)):
                    fd.writelines("{}, {}\n".format(i + 1, histogram[i]))
                fd.flush()
                fd.truncate()
                with shproto.dispatcher.histogram_lock:
                    pulses = shproto.dispatcher.pulses_buf
                    shproto.dispatcher.pulses_debug_count += len(shproto.dispatcher.pulses_buf)
                    shproto.dispatcher.pulses_buf = []
                if len(pulses) > 0 and shproto.dispatcher.pulse_file_opened != 1 and (fd_pulses := open("/tmp/pulses.csv", "w+")):
                    shproto.dispatcher.pulse_file_opened = 1
                if shproto.dispatcher.pulse_file_opened == 1:
                    for pulse in pulses:
                        fd_pulses.writelines("{}\n".format(' '.join("{:d}".format(p) for p in  pulse )))
                    fd_pulses.flush()

            print("elapsed: {}/{:.0f} cps: {}/{:.2f} total_pkts: {} drop_pkts: {} lostImp: {} cpu: {} dbg_pulses: {}".format(
               shproto.dispatcher.total_time, (datetime.now(timezone.utc) - shproto.dispatcher.start_timestamp).total_seconds(),
               shproto.dispatcher.cps, spec_pulses_total_cps,
               shproto.dispatcher.total_pkts, shproto.dispatcher.dropped,
               shproto.dispatcher.lost_impulses, shproto.dispatcher.cpu_load,
               shproto.dispatcher.pulses_debug_count))
    if (shproto.dispatcher.pulse_file_opened == 1):
        fd_pulses.close()
        shproto.dispatcher.pulse_file_opened = 0

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
