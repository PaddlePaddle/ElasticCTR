import time
import os
import socket


def net_is_used(port, ip='0.0.0.0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
        s.shutdown(2)
        print('Error: %s:%d is used' % (ip, port))
        return True
    except:
        #print('%s:%d is unused' % (ip, port))
        return False

os.system("ps -ef | grep ${USER} | grep mlflow | awk {'print $2'} | xargs kill -9 >/dev/null 2>&1")
os.system("ps -ef | grep ${USER} | grep gunicorn | awk {'print $2'} | xargs kill -9 >/dev/null 2>&1")

current_port = 8100
while True:
    if os.path.exists("./mlruns"):
        if not net_is_used(current_port):
            os.system("mlflow server --default-artifact-root ./mlruns/0 --host 0.0.0.0 --port " + str(current_port) + " >/dev/null 2>&1 &")
            time.sleep(3)
            print("mlflow ready, started at port" + str(current_port) + "!")
            exit(0)
        else:
            current_port = current_port + 1
            continue
    else:
        time.sleep(30)
