import shproto.dispatcher
import shproto.alert
import time
import threading
import re
import argparse
import os
from datetime import datetime, timezone, timedelta

spec_dir = os.environ["HOME"] + "/nanopro/"
#spec_file = spec_dir + "spectrum.csv"

shproto.dispatcher.start_timestamp = datetime.now(timezone.utc)


def helptxt():
    print("""
    Some non-hazardous commands for text mode:
        -inf
            Prints debug information and variables
        -sta
            Starts collecting impulses for histogram
        -sto
            Stops collecting impulses for histogram
        -rst
            Resets collecting
        -nos <number>
            Sets number adc value for peak detection (default value - 30).
            Lower number (for ex 12) - lowest energies peaks collected to histogram.
            
    Other common commands:
        spec_sta
            Start saving spectra to file
        spec_sto
            Stop saving spectra to file
        alert_sta
            Alert mode. Start writing individual spectra if cps > cps * ratio
        alert_sto
            Alert mode stop.
        stat
            Show statistics while spectra gathering
        rst 
            send "-rst", "-cal", "-inf"
        spd <number>
            Set port speed to <number>
        quit or exit
            Exits terminal
            
        Type serial number to use this device.
    """)


if __name__ == '__main__':
    helptxt()

    parser = argparse.ArgumentParser(
        prog='ProgramName',
        description='What the program does',
        epilog='Text at the bottom of help')
    parser.add_argument('file', default='spectrum.csv')
    parser.add_argument('-d', '--device', default='')
    parser.add_argument('-c', '--csv', action='store_true')
    parser.add_argument('-i', '--interpec_csv', action='store_true')
    parser.add_argument('-x', '--xml', action='store_true')
    parser.add_argument('-a', '--autostart', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    if not args.device == '':
        shproto.port.getportbyserialnumber(args.device)
    if re.search("^[/\.].*", args.file):
        spec_file = args.file
    else:
        spec_file = spec_dir + args.file
    if not re.search("\.csv$", spec_file, flags=re.IGNORECASE):
        spec_file = spec_file + ".csv"
    if args.csv:
        shproto.dispatcher.csv_out = 1
    else:
        shproto.dispatcher.csv_out = 0
    if args.xml:
        shproto.dispatcher.xml_out = 1
    else:
        shproto.dispatcher.xml_out = 0
    if args.interpec_csv:
        shproto.dispatcher.csv_out = 1
        shproto.dispatcher.interspec_csv = 1
    else:
        shproto.dispatcher.interspec_csv = 0
    if args.autostart:
        autostart = 1
    else:
        autostart = 0
    if args.verbose:
        shproto.dispatcher.verbose = 1
    else:
        shproto.dispatcher.verbose = 1


    print("Found devices: {}".format(shproto.port.getallportsastext()))
    dispatcher = threading.Thread(target=shproto.dispatcher.start)
    dispatcher.start()
    time.sleep(1)
    spec = threading.Thread(target=shproto.dispatcher.process_01, args=(spec_file,))
    shproto.dispatcher.spec_stopflag = 1
    alert = threading.Thread(target=shproto.alert.alertmode, args=(spec_dir, 1.5,))
    shproto.alert.alert_stop = 1
    command = ""
    auto_command = ""
    if autostart:
        auto_command = "spec_sta"
    while True:
        if auto_command != "":
            command = auto_command
            auto_command = ""
        else:
            command = input(">> ")
        if command == "exit" or command == "quit":
            shproto.dispatcher.stop()
            exit(0)
        else:
            if command == "help":
                helptxt()
                continue
            if command == "rst":
                shproto.dispatcher.process_03("-rst")
                time.sleep(2)
                shproto.dispatcher.process_03("-cal")
                time.sleep(2)
                shproto.dispatcher.process_03("-inf")
                continue
            if command == "spec_sta":
                shproto.dispatcher.process_03("-cal")
                time.sleep(2)
                shproto.dispatcher.process_03("-inf")
                time.sleep(1)
                shproto.dispatcher.process_03("-sta")
                if shproto.dispatcher.spec_stopflag == 0:
                    print("Collecting thread allready running")
                    continue
                spec.start()
                continue
            if command == "spec_sto":
                shproto.dispatcher.spec_stop()
                spec = threading.Thread(target=shproto.dispatcher.process_01, args=(spec_file,))
                continue
            if command == "alert_sta":
                if shproto.alert.alert_stop == 0:
                    print("Alert thread allready running")
                    continue
                alert.start()
                continue
            if command == "alert_sto":
                shproto.alert.stop()
                alert = threading.Thread(target=shproto.alert.alertmode, args=(spec_dir, 1.5,))
                continue
            if m := re.search("^(spd|speed)\s+(\S+)", command):
                shproto.port.port_speed = m.group(2)
                print("port speed set to {}... reconnect".format(shproto.port.port_speed))
                shproto.dispatcher.stop()
                with shproto.dispatcher.stopflag_lock:
                    shproto.dispatcher.stopflag = 0
                dispatcher = threading.Thread(target=shproto.dispatcher.start)
                dispatcher.start()
                time.sleep(1)
                continue
            if command in shproto.port.getallportssn() or re.match("^/", command):
                print("Connect to device: {}".format(shproto.port.getportbyserialnumber(command)))
                shproto.dispatcher.stop()
                with shproto.dispatcher.stopflag_lock:
                    shproto.dispatcher.stopflag = 0
                dispatcher = threading.Thread(target=shproto.dispatcher.start)
                dispatcher.start()
                time.sleep(1)
                continue
            if command == "stat":
                if shproto.dispatcher.total_pkts == 0:
                    percent = 0
                else:
                    percent = round(100 * shproto.dispatcher.dropped / shproto.dispatcher.total_pkts, 2)
                print(
                    "Histograms 0x01: {}, Commands 0x03: {}, Commands 0x04: {}, Total packets: {},"
                    " Dropped packets: {} ({})%"
                    .format(
                        shproto.dispatcher.pkts01,
                        shproto.dispatcher.pkts03,
                        shproto.dispatcher.pkts04,
                        shproto.dispatcher.total_pkts,
                        shproto.dispatcher.dropped,
                        percent
                    )
                )
                print("Total time: {}, cps: {}, cpu_load: {}, lost_imp: {}".format(shproto.dispatcher.total_time,
                                                                                   shproto.dispatcher.cps,
                                                                                   shproto.dispatcher.cpu_load,
                                                                                   shproto.dispatcher.lost_impulses))
            else:
                shproto.dispatcher.process_03(command)
