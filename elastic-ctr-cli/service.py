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

os.system("ps -ef | grep mlflow | awk {'print $2'} | xargs kill -9 >/dev/null 2>&1")
os.system("ps -ef | grep gunicorn | awk {'print $2'} | xargs kill -9 >/dev/null 2>&1")

while True:
    if os.path.exists("./mlruns") and not net_is_used(8111):
        os.system("mlflow server --default-artifact-root ./mlruns/0 --host 0.0.0.0 --port 8111 >/dev/null 2>&1 &")
        time.sleep(3)
        print("mlflow ready!")
        exit(0)
    time.sleep(30)
