import time
import shproto.dispatcher
import statistics
import threading

avg_cps = 0
alert_rised = 0

alert_stop = 0
alert_stop_lock = threading.Lock()

avg_cycles = 30
avg_cycles_timeout = 5  # sec

relax_cycles = 5
relax_ratio = 1.1
alert_loop_timeout = 5  # sec


def alertmode(spec_dir="/Users/amber/Documents/Git/nanopro/", cps_ratio=1.5):
    count = 0
    cps_arr = []
    print("Collecting average cps, this will take about {} sec.".format(avg_cycles * avg_cycles_timeout))
    while count <= avg_cycles:
        with shproto.dispatcher.cps_lock:
            current_cps = shproto.dispatcher.cps
        if current_cps > 0:
            cps_arr.append(current_cps)
            super.avg_cps = statistics.median(cps_arr)
            count += 1
        time.sleep(avg_cycles_timeout)
    print("Average cps collected: {}, starting alert mode.".format(super.avg_cps))
    cur_relax_cycles = 0
    fd = None
    while True:
        with alert_stop_lock:
            if alert_stop:
                break
        with shproto.dispatcher.cps_lock:
            current_cps = shproto.dispatcher.cps
        if not alert_rised:
            if current_cps >= cps_ratio * super.avg_cps:
                ts = time.localtime()
                filename = "{}alert_{}_{}_{}__{}_{}_{}".format(spec_dir,
                                                               ts.tm_mday,
                                                               ts.tm_mon,
                                                               ts.tm_year,
                                                               ts.tm_hour,
                                                               ts.tm_min,
                                                               ts.tm_sec)
                print("Alert rised. Current cps = {} > avg_cps = {}. Start writing spectrum {}".format(
                    current_cps,
                    avg_cps,
                    filename))
                fd = open(filename, "w")
                super.alert_rised = 1
        else:
            if current_cps <= current_cps * relax_ratio:
                cur_relax_cycles += 1
            else:
                fd.seek(0)
                for i in range(0, 8192):
                    fd.writelines("{}, {}\r\n".format(i + 1, shproto.dispatcher.histogram[i]))
                fd.flush()
                fd.truncate()
            if cur_relax_cycles > relax_cycles:
                print("Alert gone. Current cps = {}, for {} seconds".format(current_cps,
                                                                            relax_cycles * alert_loop_timeout))
                super.alert_rised = 0
                fd.close()
        time.sleep(alert_loop_timeout)
    print("Exit alert mode.")


def stop():
    with alert_stop_lock:
        super.alert_stop = 1
