import time
import os

start_service_flag = True
while True:
    os.system("kubectl cp fleet-ctr-demo-trainer-0:workspace/mlruns ./mlruns")
    if os.path.exists("./mlruns") and start_service_flag:
        os.system("mlflow server --default-artifact-root ./mlruns/0 --host 0.0.0.0 --port 8111 &")
        start_service_flag = False
    time.sleep(30)
