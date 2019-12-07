import math
import sys
import os
import paddle.fluid as fluid
import numpy as np
from criteo_pyreader import CriteoDataset
import paddle
from nets import ctr_dnn_model

feature_names = []
with open(sys.argv[1]) as fin:
    for line in fin:
        feature_names.append(line.strip())

print(feature_names)


sparse_feature_dim = 400000001
embedding_size = 9

sparse_input_ids = [fluid.layers.data(name= name, shape=[1], lod_level=1, dtype='int64')
                    for name in feature_names]
label = fluid.layers.data(name='label', shape=[1], dtype='int64')
_words = sparse_input_ids + [label]

exe = fluid.Executor(fluid.CPUPlace())
exe.run(fluid.default_startup_program())
input_folder = "../data/infer_data"
files = os.listdir(input_folder)
infer_filelist = ["{}/{}".format(input_folder, f) for f in files]
print(infer_filelist)

criteo_dataset = CriteoDataset(feature_names)

startup_program = fluid.framework.default_main_program()
test_program = fluid.framework.default_main_program()
test_reader = paddle.batch(criteo_dataset.test(infer_filelist), 1000)
_, auc_var, _ = ctr_dnn_model(embedding_size, sparse_input_ids, label, sparse_feature_dim)
[inference_program, feed_target_names, fetch_targets] = fluid.io.load_inference_model(dirname="./saved_models/",executor=exe)
with open('infer_programdesc', 'w+') as f:
    f.write(inference_program.to_string(True))
def set_zero(var_name):
    param = fluid.global_scope().var(var_name).get_tensor()
    param_array = np.zeros(param._get_dims()).astype("int64")
    param.set(param_array, fluid.CPUPlace())

auc_states_names = ['_generated_var_2', '_generated_var_3']
for name in auc_states_names:
    set_zero(name)
inputs = _words
feeder = fluid.DataFeeder(feed_list = inputs, place = fluid.CPUPlace())
for batch_id, data in enumerate(test_reader()):
    auc_val = exe.run(inference_program,
                      feed=feeder.feed(data),
                      fetch_list=fetch_targets)
print(auc_val)

