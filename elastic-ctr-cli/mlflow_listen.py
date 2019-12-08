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

import time
import os

start_service_flag = True
while True:
    os.system("kubectl cp fleet-ctr-demo-trainer-0:workspace/mlruns ./mlruns")
    if os.path.exists("./mlruns") and start_service_flag:
        os.system("mlflow server --default-artifact-root ./mlruns/0 --host 0.0.0.0 --port 8111 &")
        start_service_flag = False
    time.sleep(30)
