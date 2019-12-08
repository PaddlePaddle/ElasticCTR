#!/usr/bin/env python
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

import argparse
import logging
import struct
import time
import datetime
import json
from collections import OrderedDict
import numpy as np
import os
import paddle
import paddle.fluid as fluid
import math


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fluid")
logger.setLevel(logging.INFO)

NOW_TIMESTAMP = time.time()
NOW_DATETIME = datetime.datetime.now().strftime("%Y%m%d")

sparse_feature_dim = 100000001
embedding_size = 9


def parse_args():
    parser = argparse.ArgumentParser(description="PaddlePaddle DeepFM example")
    parser.add_argument(
        '--model_path',
        type=str,
        required=True,
        help="The path of model parameters file")
    parser.add_argument(
        '--output_data_path',
        type=str,
        default="/save_program/ctr_cube/",
        help="The path of dump output")

    return parser.parse_args()


def write_donefile(base_datafile, base_donefile):
    dict = OrderedDict()
    if not os.access(os.path.dirname(base_donefile), os.F_OK):
        os.makedirs(os.path.dirname(base_donefile))
    dict["id"] = str(int(NOW_TIMESTAMP))
    dict["key"] = dict["id"]
    dict["input"] = os.path.dirname(base_datafile)
    with open(base_donefile, "a") as f:
        jsonstr = json.dumps(dict) + '\n'
        f.write(jsonstr)


def dump():
    args = parse_args()
    feature_names = []

    output_data_path = os.path.abspath(args.output_data_path)
    base_datadir = output_data_path + "/" + NOW_DATETIME + "/base"
    try:
        os.makedirs(base_datadir)
    except:
        print ('Dir already exist, skip.')
    base_datafile = output_data_path + "/" + NOW_DATETIME + "/base/feature"
    write_base_datafile = "/output/ctr_cube/" + NOW_DATETIME + "/base/feature"
    base_donefile = output_data_path + "/" + "donefile/" + "base.txt"
    os.system('/save_program/parameter_to_seqfile ' + args.model_path +'/SparseFeatFactors ' + base_datafile)
    write_donefile(write_base_datafile + "0", base_donefile)


if __name__ == '__main__':
    dump()

