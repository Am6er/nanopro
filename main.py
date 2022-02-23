import shproto.dispatcher
import shproto.alert
import time
import threading

spec_dir = "/Users/amber/Documents/Git/nanopro/"
spec_file = spec_dir + "spectrum.csv"


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
        quit or exit
            Exits terminal
            
        Type serial number to use this device.
    """)


if __name__ == '__main__':
    helptxt()
    print("Found devices: {}".format(shproto.port.getallportsastext()))
    dispatcher = threading.Thread(target=shproto.dispatcher.start)
    dispatcher.start()
    time.sleep(1)
    spec = threading.Thread(target=shproto.dispatcher.process_01, args=(spec_file,))
    alert = threading.Thread(target=shproto.alert.alertmode, args=(spec_dir, 1.5,))
    command = ""
    while True:
        command = input(">> ")
        if command == "exit" or command == "quit":
            shproto.dispatcher.stop()
            exit(0)
        else:
            if command == "help":
                helptxt()
                continue
            if command == "spec_sta":
                spec.start()
                continue
            if command == "spec_sto":
                shproto.dispatcher.spec_stop()
                continue
            if command == "alert_sta":
                alert.start()
            if command == "alert_sto":
                shproto.alert.stop()
            if command in shproto.port.getallportssn():
                print("Connect to device: {}".format(shproto.port.getportbyserialnumber(command)))
                shproto.dispatcher.stop()
                with shproto.dispatcher.stopflag_lock:
                    shproto.dispatcher.stopflag = 0
                dispatcher = threading.Thread(target=shproto.dispatcher.start, args=(command,))
                dispatcher.start()
                time.sleep(1)
                continue
            if command == "stat":
                print(
                    "Histograms 0x01: {}, Commands 0x03: {}, Commands 0x04: {}, Total: {}".format(
                        shproto.dispatcher.pkts01,
                        shproto.dispatcher.pkts03,
                        shproto.dispatcher.pkts04,
                        shproto.dispatcher.total_pkts))
                print("Total time: {}, cps: {}, cpu_load: {}, lost_imp: {}".format(shproto.dispatcher.total_time,
                                                                                   shproto.dispatcher.cps,
                                                                                   shproto.dispatcher.cpu_load,
                                                                                   shproto.dispatcher.lost_impulses))
            else:
                shproto.dispatcher.process_03(command)
