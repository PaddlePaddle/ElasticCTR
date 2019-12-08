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
import mlflow
from paddle.fluid.incubate.fleet.parameter_server.distribute_transpiler import fleet
from paddle.fluid.incubate.fleet.base import role_maker
from paddle.fluid.transpiler.distribute_transpiler import DistributeTranspilerConfig
from paddle.fluid.contrib.utils.hdfs_utils import HDFSClient
from nets import ctr_dnn_model
import subprocess as sp
import time
import psutil
import matplotlib
import matplotlib.pyplot as plt
from collections import OrderedDict
from datetime import datetime, timedelta
import json
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    file_server_addr = os.environ["FILE_SERVER_SERVICE_HOST"] + ":"+ os.environ["FILE_SERVER_SERVICE_PORT"]
    slot_res = os.system('wget '+ file_server_addr + '/slot.conf')
    if slot_res !=0:
        raise ValueError('No Slot Conf Found.')
    feature_names = []
    with open(sys.argv[1]) as fin:
        for line in fin:
            feature_names.append(line.strip())
    logger.info("Slot:" + str(feature_names))
except ValueError as e:
    print(e)
    sys.exit(1)

sparse_input_ids = [
    fluid.layers.data(name=name, shape=[1], lod_level=1, dtype='int64')
    for name in feature_names]

label = fluid.layers.data(
    name='label', shape=[1], dtype='int64')

sparse_feature_dim = int(os.environ['SPARSE_DIM'])
embedding_size = 9
epochs = 1
dataset_prefix = os.environ['DATASET_PATH']

avg_cost, auc_var, _ = ctr_dnn_model(embedding_size, sparse_input_ids, label, sparse_feature_dim)

start_date_hr = datetime.strptime(os.environ['START_DATE_HR'], '%Y%m%d/%H')
end_date_hr = datetime.strptime(os.environ['END_DATE_HR'], '%Y%m%d/%H')
current_date_hr = start_date_hr
hdfs_address = os.environ['HDFS_ADDRESS']
hdfs_ugi = os.environ['HDFS_UGI']
start_run_flag = True
role = role_maker.UserDefinedRoleMaker(
    current_id=int(os.getenv("CURRENT_ID")),
    role=role_maker.Role.WORKER
    if os.getenv("TRAINING_ROLE") == "TRAINER" else role_maker.Role.SERVER,
    worker_num=int(os.getenv("PADDLE_TRAINERS_NUM")),
    server_endpoints=os.getenv("ENDPOINTS").split(","))

role = role_maker.PaddleCloudRoleMaker()
fleet.init(role)

config = DistributeTranspilerConfig()
config.sync_mode = False
optimizer = fluid.optimizer.SGD(0.0001)
optimizer = fleet.distributed_optimizer(optimizer, config)
optimizer.minimize(avg_cost)
DATE_TIME_STRING_FORMAT = '%Y%m%d/%H'
if fleet.is_server():
    fleet.init_server()
    fleet.run_server()
elif fleet.is_worker():
    place = fluid.CPUPlace()
    exe = fluid.Executor(place)
    fleet.init_worker()
    exe.run(fluid.default_startup_program())
    logger.info("startup program done.")
    if fleet.is_first_worker():
        plt.figure()
        y_auc = []
        y_cpu = []
        y_memory = []
        y_network_sent = []
        y_network_recv = []
        x_list = []
        x = 0
        last_net_sent = psutil.net_io_counters().bytes_sent
        last_net_recv = psutil.net_io_counters().bytes_recv

    while True:

        #hadoop fs -D hadoop.job.ugi=root, -D fs.default.name=hdfs://192.168.48.87:9000 -ls /
        current_date_hr_exist = os.system('hadoop fs -D hadoop.job.ugi=' + hdfs_ugi + ' -D fs.defaultFS=' + hdfs_address +
                        ' -ls ' + os.path.join(dataset_prefix,  current_date_hr.strftime(DATE_TIME_STRING_FORMAT), 'donefile') +' >/dev/null 2>&1')

        if current_date_hr_exist:
            pass
        else:
            """
            output = sp.check_output("hdfs dfs -ls hdfs://192.168.48.189:9000/train_data | awk '{if(NR>1) print $8}'",
                                     shell=True)
            print(output)
            train_filelist = ["{}".format(f) for f in output.decode('ascii').strip().split('\n')]
            print(train_filelist)
            for i in range(len(train_filelist)):
                train_filelist[i] = train_filelist[i].split("/")[-1]
            train_filelist.sort(reverse=True)
            print(train_filelist)
            """

            dataset = fluid.DatasetFactory().create_dataset()
            dataset.set_use_var(sparse_input_ids + [label])
            pipe_command = "python criteo_dataset.py {}".format(sys.argv[1])
            dataset.set_pipe_command(pipe_command)
            dataset.set_batch_size(32)
            dataset.set_hdfs_config(hdfs_address, hdfs_ugi)
            dataset.set_thread(10)
            exe = fluid.Executor(fluid.CPUPlace())
            input_folder = "hdfs:"
            output = sp.check_output( "hadoop fs -D hadoop.job.ugi=" + hdfs_ugi
                                      + " -D fs.defaultFS=" + hdfs_address +" -ls " + os.path.join(dataset_prefix, str(current_date_hr.strftime(DATE_TIME_STRING_FORMAT))) + "/ | awk '{if(NR>1) print $8}'", shell=True)
            train_filelist = ["{}{}".format(input_folder, f) for f in output.decode('ascii').strip().split('\n')]
            train_filelist.remove('hdfs:' + os.path.join(dataset_prefix, str(current_date_hr.strftime(DATE_TIME_STRING_FORMAT)), 'donefile'))
            #pending
            step = 0

            config = DistributeTranspilerConfig()
            config.sync_mode = False

            # if is worker
            fleet_filelist = fleet.split_files(train_filelist)
            print(fleet_filelist)
            logger.info( "Training: " + current_date_hr.strftime(DATE_TIME_STRING_FORMAT))
            dataset.set_filelist(fleet_filelist)
            if fleet.is_first_worker():
                # experiment_id = mlflow.create_experiment("fleet-ctr")
                if start_run_flag:
                    mlflow.start_run()
                    mlflow.log_param("sparse_feature_dim", sparse_feature_dim)
                    mlflow.log_param("embedding_size", embedding_size)
                    mlflow.log_param("selected_slots", feature_names)
                    mlflow.log_param("epochs_num", epochs)
                    mlflow.log_param("physical_cpu_counts", psutil.cpu_count(logical=False))
                    mlflow.log_param("logical_cpu_counts", psutil.cpu_count())
                    mlflow.log_param("total_memory/GB",
                                     round(psutil.virtual_memory().total / (1024.0 * 1024.0 * 1024.0), 3))
                    start_run_flag = False


                class FH(fluid.executor.FetchHandler):
                    def handler(self, fetch_target_vars):
                        auc = fetch_target_vars[0]
                        print("test metric auc: ", fetch_target_vars)
                        global last_net_sent
                        global last_net_recv
                        global y_auc
                        global y_cpu
                        global y_memory
                        global y_network_sent
                        global y_network_recv
                        global x
                        mlflow.log_metric("network_bytes_sent_speed",
                                          psutil.net_io_counters().bytes_sent - last_net_sent)
                        mlflow.log_metric("network_bytes_recv_speed",
                                          psutil.net_io_counters().bytes_recv - last_net_recv)
                        y_network_sent.append((psutil.net_io_counters().bytes_sent - last_net_sent)/10)
                        y_network_recv.append((psutil.net_io_counters().bytes_recv - last_net_recv)/10)
                        last_net_sent = psutil.net_io_counters().bytes_sent
                        last_net_recv = psutil.net_io_counters().bytes_recv
                        mlflow.log_metric("cpu_usage_total", round((psutil.cpu_percent(interval=0) / 100), 3))
                        y_cpu.append(round((psutil.cpu_percent(interval=0) / 100), 3))
                        mlflow.log_metric("free_memory/GB",
                                          round(psutil.virtual_memory().free / (1024.0 * 1024.0 * 1024.0), 3))
                        mlflow.log_metric("memory_usage",
                                          round((psutil.virtual_memory().total - psutil.virtual_memory().free)
                                                / float(psutil.virtual_memory().total), 3))
                        y_memory.append(round((psutil.virtual_memory().total - psutil.virtual_memory().free)
                                              / float(psutil.virtual_memory().total), 3))
                        if auc == None:
                            mlflow.log_metric("auc", 0.5)
                            auc = [0.5]
                        else:
                            mlflow.log_metric("auc", auc[0])
                        y_auc.append(auc)
                        x_list.append(x)
                        
                        if x >= 120: # in the future 120 will be replaced by 24*60*60 which means one day length
                            y_auc.pop(0)
                            y_cpu.pop(0)
                            y_memory.pop(0)
                            y_network_recv.pop(0)
                            y_network_sent.pop(0)
                            x_list.pop(0)
                        x += 10
                        if x % 60 == 0 and x != 0:
                            plt.subplot(221)
                            plt.plot(x_list, y_auc)
                            plt.title('auc')
                            plt.grid(True)

                            plt.subplot(222)
                            plt.plot(x_list, y_cpu)
                            plt.title('cpu_usage')
                            plt.grid(True)

                            plt.subplot(223)
                            plt.plot(x_list, y_memory)
                            plt.title('memory_usage')
                            plt.grid(True)

                            plt.subplot(224)
                            plt.plot(x_list, y_network_sent, label="network_sent_speed")
                            plt.plot(x_list, y_network_recv, label="network_recv_speed")
                            plt.title('network_speed')
                            plt.grid(True)

                            plt.subplots_adjust(top=0.9, bottom=0.2, hspace=0.4, wspace=0.35)
                            plt.legend(bbox_to_anchor=(0, -0.6), loc='lower left', borderaxespad=0.)
                            temp_file_name = "dashboard_" + time.strftime('%Y-%m-%d_%H:%M:%S',
                                                                          time.localtime(time.time())) + ".png"
                            plt.savefig(temp_file_name, dpi=250)
                            sys.stdout.flush()
                            plt.clf()
                            os.system("rm -f "+str(mlflow.get_artifact_uri().split(":")[1]) + "/*.png")
                            mlflow.log_artifact(local_path=temp_file_name)
                            sys.stdout.flush()
                            os.system("rm -f ./*.png")
                            sys.stdout.flush()
                            logger.info(str(mlflow.get_artifact_uri().split(":")[1]))
                            sys.stdout.flush()

                os.system("hadoop fs -D hadoop.job.ugi=" + hdfs_ugi  + " -D fs.defaultFS=" + hdfs_address
                          + " -rm  " + os.path.join(dataset_prefix, str(current_date_hr.strftime(DATE_TIME_STRING_FORMAT))+ "_model/donefile") + " >/dev/null 2>&1")
                for i in range(epochs):
                    exe.train_from_dataset(
                        program=fluid.default_main_program(),
                        dataset=dataset,
                        fetch_handler=FH([auc_var.name], 10, True),
                        # fetch_list=[auc_var],
                        # fetch_info=["auc"],
                        debug=False)
                path = "./saved_models/" + current_date_hr.strftime(DATE_TIME_STRING_FORMAT) + "_model/"
                logger.info("save inference program: " +  path)
                if len(y_auc) <=1:                
                    logger.info("Current AUC: " + str(y_auc[-1]))
                else:
                    logger.info("Dataset is too small, cannot get AUC.")
                fetch_list = fleet.save_inference_model(exe,
                                                        path,
                                                        [x.name for x in sparse_input_ids] + [label.name],
                                                        [auc_var])
                os.system("hadoop fs -D hadoop.job.ugi=" + hdfs_ugi  + " -D fs.defaultFS=" + hdfs_address
                          + " -put -f "+ path +" " + os.path.join(dataset_prefix, current_date_hr.strftime(DATE_TIME_STRING_FORMAT).split("/")[0]) + " >/dev/null 2>&1")
                os.system('touch donefile')
                os.system("hadoop fs -D hadoop.job.ugi=" + hdfs_ugi + " -D fs.defaultFS=" + hdfs_address
                          + " -put -f donefile" + " " + os.path.join(dataset_prefix,  current_date_hr.strftime(DATE_TIME_STRING_FORMAT) + "_model/") +" >/dev/null 2>&1")
                logger.info("push raw model to HDFS: " + current_date_hr.strftime(DATE_TIME_STRING_FORMAT))
                os.system('python process_rawmodel.py ' + './saved_models/' + current_date_hr.strftime(DATE_TIME_STRING_FORMAT) + "_model " + current_date_hr.strftime(DATE_TIME_STRING_FORMAT) + " >/dev/null 2>&1")
                os.system("hadoop fs -D hadoop.job.ugi=" + hdfs_ugi + " -D fs.defaultFS=" + hdfs_address
                           + " -put -f ctr_model.tar.gz " + " /output/")
                os.system("hadoop fs -D hadoop.job.ugi=" + hdfs_ugi + " -D fs.defaultFS=" + hdfs_address
                           + " -put -f ctr_cube " + " /output/")
                logger.info("push converted model to HDFS: " + current_date_hr.strftime(DATE_TIME_STRING_FORMAT))
                os.system("rm -rf " + path)
                logger.info(current_date_hr.strftime(DATE_TIME_STRING_FORMAT) + ' Training Done.')
            else:
                for i in range(epochs):
                    exe.train_from_dataset(
                        program=fleet.main_program,
                        dataset=dataset,
                        # fetch_list=[auc_var],
                        # fetch_info=["auc"],
                        debug=False)
                while True:
                    rawmodel_donefile_exist = os.system("hadoop fs -D hadoop.job.ugi=" + hdfs_ugi + " -D fs.defaultFS=" + hdfs_address
                          + " -ls "+ os.path.join(dataset_prefix, current_date_hr.strftime(DATE_TIME_STRING_FORMAT) + "_model/donefile") +" >/dev/null 2>&1")
                    if not rawmodel_donefile_exist:
                        break
        if end_date_hr == current_date_hr:
            mlflow.end_run()
            break
        current_date_hr = current_date_hr + timedelta(hours=1)

