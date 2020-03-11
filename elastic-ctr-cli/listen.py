import time
import os
import socket


def rewrite_yaml(path):
    for root , dirs, files in os.walk(path):
        for name in files:
            if name == "meta.yaml":
                if len(root.split("/mlruns")) != 2:
                    print("Error: the parent directory of your current directory should not contain a path named mlruns")
                    exit(0)
                cmd = "sed -i \"s#/workspace#" + root.split("/mlruns")[0] + "#g\" " + os.path.join(root, name)
                os.system(cmd)

time.sleep(5)
os.system("rm -rf ./mlruns >/dev/null 2>&1")
while True:
    r = os.popen("kubectl get pod | grep fleet-ctr-demo-trainer-0 | awk {'print $3'}") 
    info = r.readlines()
    if info == []:
        exit(0)
    for line in info:
        line = line.strip() 
        if line == "Completed" or line == "Terminating":
            exit(0)
    os.system("kubectl cp fleet-ctr-demo-trainer-0:workspace/mlruns ./mlruns_temp >/dev/null 2>&1")
    if os.path.exists("./mlruns_temp"):
        os.system("rm -rf ./mlruns >/dev/null 2>&1")
        os.system("mv ./mlruns_temp ./mlruns >/dev/null 2>&1")
        rewrite_yaml(os.getcwd()+"/mlruns")
    time.sleep(30)
