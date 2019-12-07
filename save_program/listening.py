import time
import os
import json

previous_last_line = ""
while True:
    try:
        with open("/share/saved_models/model_donefile","r") as f:
            lines = f.readlines()
            current_line = lines[-1]
            path = json.loads(current_line)['path']
            
            if current_line != previous_last_line:
                os.system("python3 save_program slot.conf .")
                os.system("python dumper_multiprocessing.py 
                os.system("python replace_params.py " +
                          "--model_dir " + path + 
                         " --inference_only_model_dir " + path+"../inference_only")
            else:
                pass
            previous_last_line = current_line
    except Exception,err:
        pass

