import os
import sys

os.system('python3 /save_program/save_program.py slot.conf . ' + sys.argv[2])
os.system('python3 /save_program/dumper.py --model_path ' + sys.argv[1] + ' --output_data_path ctr_cube/')
os.system('python3 /save_program/replace_params.py --model_dir ' + sys.argv[1] +' --inference_only_model_dir inference_only')
os.system('tar czf ctr_model.tar.gz inference_only/')
