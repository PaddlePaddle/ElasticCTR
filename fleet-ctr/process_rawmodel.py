#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

os.system('python3 /save_program/save_program.py slot.conf . ' + sys.argv[2])
os.system('python3 /save_program/dumper.py --model_path ' + sys.argv[1] + ' --output_data_path ctr_cube/')
os.system('python3 /save_program/replace_params.py --model_dir ' + sys.argv[1] +' --inference_only_model_dir inference_only')
os.system('tar czf ctr_model.tar.gz inference_only/')
