#!/usr/bin/python
# Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
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

import math
import sys
import os
import paddle.fluid as fluid
import subprocess as sp
from paddle.fluid.incubate.fleet.parameter_server.distribute_transpiler import fleet
from paddle.fluid.incubate.fleet.base import role_maker
from paddle.fluid.transpiler.distribute_transpiler import DistributeTranspilerConfig

file_server_addr = os.environ["FILE_SERVER_SERVICE_HOST"] + ":"+ os.environ["FILE_SERVER_SERVICE_PORT"]
os.system('wget '+ file_server_addr + '/slot.conf')

feature_names = []
with open(sys.argv[1]) as fin:
    for line in fin:
        feature_names.append(line.strip())

print(feature_names)

sparse_input_ids = [
    fluid.layers.data(name=name, shape=[1], lod_level=1, dtype='int64')
    for name in feature_names]

label = fluid.layers.data(
    name='label', shape=[1], dtype='int64')

sparse_feature_dim = 100000001
embedding_size = 9


def embedding_layer(input):
    emb = fluid.layers.embedding(
        input=input,
        is_sparse=True,
        is_distributed=False,
        size=[sparse_feature_dim, embedding_size],
        param_attr=fluid.ParamAttr(name="SparseFeatFactors",
                                   initializer=fluid.initializer.Uniform()))
    emb_sum = fluid.layers.sequence_pool(input=emb, pool_type='sum')
    return emb_sum

emb_sums = list(map(embedding_layer, sparse_input_ids))
concated = fluid.layers.concat(emb_sums, axis=1)
fc1 = fluid.layers.fc(input=concated, size=400, act='relu',
                      param_attr=fluid.ParamAttr(initializer=fluid.initializer.Normal(
                          scale=1 / math.sqrt(concated.shape[1]))))
fc2 = fluid.layers.fc(input=fc1, size=400, act='relu',
                      param_attr=fluid.ParamAttr(
                          initializer=fluid.initializer.Normal(
                              scale=1 / math.sqrt(fc1.shape[1]))))
fc3 = fluid.layers.fc(input=fc2, size=400, act='relu',
                      param_attr=fluid.ParamAttr(
                          initializer=fluid.initializer.Normal(
                              scale=1 / math.sqrt(fc2.shape[1]))))

predict = fluid.layers.fc(input=fc3, size=2, act='softmax',
                          param_attr=fluid.ParamAttr(initializer=fluid.initializer.Normal(
                              scale=1 / math.sqrt(fc3.shape[1]))))

cost = fluid.layers.cross_entropy(input=predict, label=label)
avg_cost = fluid.layers.reduce_sum(cost)
accuracy = fluid.layers.accuracy(input=predict, label=label)
auc_var, batch_auc_var, auc_states = \
    fluid.layers.auc(input=predict, label=label, num_thresholds=2 ** 12, slide_steps=20)

dataset = fluid.DatasetFactory().create_dataset()
dataset.set_use_var(sparse_input_ids + [label])
pipe_command = "python criteo_dataset.py {}".format(sys.argv[1])
dataset.set_pipe_command(pipe_command)
dataset.set_batch_size(32)
dataset.set_thread(10)
dataset.set_hdfs_config("hdfs://192.168.48.87:9000", "root,")
optimizer = fluid.optimizer.SGD(0.0001)
#optimizer.minimize(avg_cost)
exe = fluid.Executor(fluid.CPUPlace())

input_folder = "hdfs:"
output = sp.check_output("hdfs dfs -ls /train_data | awk '{if(NR>1) print $8}'", shell=True)
train_filelist = ["{}{}".format(input_folder, f) for f in output.decode('ascii').strip().split('\n')]
role = role_maker.PaddleCloudRoleMaker()
fleet.init(role)


config = DistributeTranspilerConfig()
config.sync_mode = False

optimizer = fleet.distributed_optimizer(optimizer, config)
optimizer.minimize(avg_cost)


if fleet.is_server():
    fleet.init_server()
    fleet.run_server()
elif fleet.is_worker():
    place = fluid.CPUPlace()
    exe = fluid.Executor(place)
    fleet.init_worker()
    exe.run(fluid.default_startup_program())
    print("startup program done.")
    fleet_filelist = fleet.split_files(train_filelist)
    dataset.set_filelist(fleet_filelist)
    exe.train_from_dataset(
        program=fluid.default_main_program(),
        dataset=dataset,
        fetch_list=[auc_var],
        fetch_info=["auc"],
        debug=True)
    print("end .... ")
# save model here

