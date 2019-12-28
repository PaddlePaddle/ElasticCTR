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
import google.protobuf.text_format as text_format
import paddle.fluid.proto.framework_pb2 as framework_pb2
import paddle.fluid.core as core
import six
import subprocess as sp

inference_path = sys.argv[2]+ '/inference_only'
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

sparse_feature_dim = int(os.environ['SPARSE_DIM'])
dataset_prefix = os.environ['DATASET_PATH']
embedding_size = 9

current_date_hr = sys.argv[3]
hdfs_address = os.environ['HDFS_ADDRESS']
hdfs_ugi = os.environ['HDFS_UGI']

def embedding_layer(input):
    emb = fluid.layers.embedding(
        input=input,
        is_sparse=True,
        is_distributed=False,
        size=[sparse_feature_dim, embedding_size],
        param_attr=fluid.ParamAttr(name="SparseFeatFactors",
                                   initializer=fluid.initializer.Uniform()))
    emb_sum = fluid.layers.sequence_pool(input=emb, pool_type='sum')
    return emb, emb_sum

emb_sums = list(map(embedding_layer, sparse_input_ids))

emb_list = [x[0] for x in emb_sums]
sparse_embed_seq = [x[1] for x in emb_sums]
inference_feed_vars = emb_list

concated = fluid.layers.concat(sparse_embed_seq, axis=1) 
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

def save_program():
    dataset = fluid.DatasetFactory().create_dataset()
    dataset.set_use_var(sparse_input_ids + [label])
    pipe_command = "python criteo_dataset.py {}".format(sys.argv[1])
    dataset.set_pipe_command(pipe_command)
    dataset.set_batch_size(32)
    dataset.set_thread(10)
    optimizer = fluid.optimizer.SGD(0.0001)
    optimizer.minimize(avg_cost)
    exe = fluid.Executor(fluid.CPUPlace())

    input_folder = "hdfs:"
    output = sp.check_output( "hadoop fs -D hadoop.job.ugi=" + hdfs_ugi
                              + " -D fs.defaultFS=" + hdfs_address +" -ls " + os.path.join(dataset_prefix, current_date_hr) + "/ | awk '{if(NR>1) print $8}'", shell=True)
    train_filelist = ["{}{}".format(input_folder, f) for f in output.decode('ascii').strip().split('\n')]
    train_filelist.remove('hdfs:' + os.path.join(dataset_prefix, current_date_hr, 'donefile'))
    train_filelist = [train_filelist[0]] 
    print(train_filelist)

    exe.run(fluid.default_startup_program())
    print("startup save program done.")
    dataset.set_filelist(train_filelist)
    exe.train_from_dataset(
        program=fluid.default_main_program(),
        dataset=dataset,
        fetch_list=[auc_var],
        fetch_info=["auc"],
        debug=False,)
        #print_period=10000)
    # save model here
    fetch_list = fluid.io.save_inference_model(inference_path, [x.name for x in inference_feed_vars], [predict], exe)


def prune_program():
    model_dir = inference_path
    model_file = model_dir + "/__model__"
    with open(model_file, "rb") as f:
        protostr = f.read()
    f.close()
    proto = framework_pb2.ProgramDesc.FromString(six.binary_type(protostr))
    block = proto.blocks[0]
    kept_ops = [op for op in block.ops if op.type != "lookup_table"]
    del block.ops[:]
    block.ops.extend(kept_ops)

    kept_vars = [var for var in block.vars if var.name != "SparseFeatFactors"]
    del block.vars[:]
    block.vars.extend(kept_vars)

    with open(model_file, "wb") as f:
        f.write(proto.SerializePartialToString())
    f.close()
    with open(model_file + ".prototxt.pruned", "w") as f:
        f.write(text_format.MessageToString(proto))
    f.close()


def remove_embedding_param_file():
    model_dir = inference_path
    embedding_file = model_dir + "/SparseFeatFactors"
    os.remove(embedding_file)


if __name__ == '__main__':
    save_program()
    prune_program()
    remove_embedding_param_file()
