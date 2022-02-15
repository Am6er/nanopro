import shproto.dispatcher
import time
import threading


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
    """)


if __name__ == '__main__':
    dispatcher = threading.Thread(target=shproto.dispatcher.start)
    dispatcher.start()
    time.sleep(1)
    spec = threading.Thread(target=shproto.dispatcher.process_01)
    command = ""
    sn = None
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
