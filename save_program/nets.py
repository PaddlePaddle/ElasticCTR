from __future__ import print_function

import argparse
import logging
import os
import time
import math
import numpy as np
import six
import paddle
import paddle.fluid as fluid
import paddle.fluid.proto.framework_pb2 as framework_pb2
import paddle.fluid.core as core

from multiprocessing import cpu_count

def ctr_dnn_model(embedding_size, sparse_input_ids, label,
                  sparse_feature_dim):
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
    return avg_cost, auc_var, batch_auc_var
