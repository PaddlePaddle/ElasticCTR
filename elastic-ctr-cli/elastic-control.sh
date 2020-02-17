#!/bin/bash
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
###############################################################################
# Function definitions
###############################################################################
help()
{
    echo "Usage: sh elastic-control.sh [COMMAND] [OPTIONS]"
    echo "elastic-control is command line interface with ELASTIC CTR"
    echo ""
    echo "Commands:"
    echo "-r|--config_resource  Configure training resource requirments. See bellow"
    echo "-a|--apply            Apply configurations to start training process"
    echo "-l|--log              Log the status of training, please make sure you have started the training process"
    echo "-c|--config_client    Retrieve client binaries to send infer requests and receive results"
    echo ""
    echo "Options(Used only for --config_resource):"
    echo "-u|--cpu              CPU cores for each training node (Unused for now)"
    echo "-m|--mem              Memory for each training node (Unused for now)"
    echo "-t|--trainer          Number of trainer nodes"
    echo "-p|--pserver          Number of parameter-server nodes"
    echo "-b|--cube             Number of cube shards"
    echo "-f|--datafile         Data file path (Only HDFS supported) (Unused for now)"
    echo "-s|--slot_conf        Slot config file"
    echo ""
    echo "Example:"
    echo "sh elastic-control.sh -r -u 4 -m 20 -t 2 -p 2 -b 5 -s slot.conf -f data.config"
    echo "sh elastic-control.sh -a"
    echo "sh elastic-control.sh -c"
    echo ""
    echo "Notes:"
    echo "Slot Config File: Specify which feature ids are used in training. One number per line."
}

die()
{
    echo "[FAILED] ${1}"
    exit 1
}

ok()
{
    echo "[OK] ${1}"
}

check_tools()
{
    if [ $# -lt 1 ]; then
        echo "Usage: check_tools COMMAND [COMMAND...]"
        return
    fi
    while [ $# -ge 1 ]; do
        type $1 &>/dev/null || die "$1 is needed but not found. Aborting..."
        shift
    done
    return 0
}

function check_files()
{
    if [ $# -lt 1 ]; then
        echo "Usage: check_files COMMAND [COMMAND...]"
        return
    fi
    while [ $# -ge 1 ]; do
        [ -f "$1" ] || die "$1 does not exist"
        shift
    done
    return 0
}

function start_fileserver()
{
    unset http_proxy
    unset https_proxy
    kubectl get pod | grep file-server >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        kubectl apply -f fileserver.yaml
    else
        echo "delete duplicate file server..."
        kubectl delete -f fileserver.yaml
        kubectl apply -f fileserver.yaml
    fi    
}

function install_volcano() {
    unset http_proxy
    unset https_proxy
    kubectl get crds | grep jobs.batch.volcano.sh >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "volcano not found, now install"
        kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml
    fi

}


function config_client()
{
    check_tools wget kubectl
    wget --no-check-certificate https://paddle-serving.bj.bcebos.com/data/ctr_prediction/elastic_ctr_client_million.tar.gz
    tar zxvf elastic_ctr_client_million.tar.gz
    rm elastic_ctr_client_million.tar.gz

    for number in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        SERVING_IP=`kubectl get services | grep 'paddleserving' | awk '{print $4}'`
        echo "searching Paddle Serving external IP, wait a moment."
        if [ "${SERVING_IP}" == "<pending>" ]; then
            sleep 10
        else
            break
        fi
    done

    SERVING_IP=`kubectl get services | grep 'paddleserving' | awk '{print $4}'`
    SERVING_PORT=`kubectl get services | grep 'paddleserving' | awk '{print $5}' | awk -F':' '{print $1}'`
    SERVING_ADDR="$SERVING_IP:$SERVING_PORT"
    sed -e "s#<$ SERVING_LIST $>#$SERVING_ADDR#g" client/template/predictors.prototxt.template > client/conf/predictors.prototxt
    FILESERVER_IP=`kubectl get services | grep 'file-server' | awk '{print $4}'`
    FILESERVER_PORT=`kubectl get services | grep 'file-server' | awk '{print $5}' | awk -F':' '{print $1}'`
    wget http://$FILESERVER_IP:$FILESERVER_PORT/slot.conf -O client/conf/slot.conf
    cp api/lib/*.so client/bin/
    echo "Done."
    echo "============================================"
    echo ""
    echo "Try ELASTIC CTR:"
    echo "1. cd client"
    echo "2. (python) python bin/elastic_ctr.py $SERVING_IP $SERVING_PORT conf/slot.conf data/ctr_prediction/data.txt"
    echo "3. (C++ native) bin/elastic_ctr_demo --test_file data/ctr_prediction/data.txt"
    return 0
}

function generate_cube_yaml()
{
    if [ $# != 1 ]; then
        echo "Invalid argument to function generate_cube_yaml"
        return -1
    fi
    if [ "$1" -lt 1 ]; then
        echo "CUBE_SHARD_NUM must not be less than 1"
        return -1
    fi
    CNT=$(($1-1))
    CUBE_SHARD_NUM=$1
    for i in `seq 0 $CNT`; do
        echo "---"
        echo "apiVersion: v1"
        echo "kind: Pod"
        echo "metadata:"
        echo "  name: cube-$i"
        echo "  labels:"
        echo "    app: cube-$i"
        echo "spec:"
        echo "  containers:"
        echo "  - name: cube-$i"
        echo "    image: hub.baidubce.com/ctr/cube:v1"
        echo "    workingDir: /cube"
        echo "    command: ['/bin/bash']"
        echo "    args: ['start.sh']"
        echo "    env:"
        echo "      - name: CUBE_SHARD_NUM"
        echo "        value: \"$CUBE_SHARD_NUM\""
        echo "    ports:"
        echo "    - containerPort: 8001"
        echo "      name: cube-agent"
        echo "    - containerPort: 8027"
        echo "      name: cube-server"
        echo "---"
        echo "kind: Service"
        echo "apiVersion: v1"
        echo "metadata:"
        echo "  name: cube-$i"
        echo "spec:"
        echo "  ports:"
        echo "    - name: agent"
        echo "      port: 8001"
        echo "      protocol: TCP"
        echo "    - name: server"
        echo "      port: 8027"
        echo "      protocol: TCP"
        echo "  selector:"
        echo "    app: cube-$i"
    done > cube.yaml
    {
        echo "apiVersion: v1"
        echo "kind: Pod"
        echo "metadata:"
        echo "  name: cube-transfer"
        echo "  labels:"
        echo "    app: cube-transfer"
        echo "spec:"
        echo "  containers:"
        echo "  - name: cube-transfer"
        echo "    image: hub.baidubce.com/ctr/cube-transfer:v2"
        echo "    workingDir: /"
        echo "    env:"
        echo "      - name: POD_IP"
        echo "        valueFrom:"
        echo "          fieldRef:"
        echo "            apiVersion: v1"
        echo "            fieldPath: status.podIP"
        echo "      - name: CUBE_SHARD_NUM"
        echo "        value: \"$CUBE_SHARD_NUM\""
        echo "    command: ['bash']"
        echo "    args: ['nonstop.sh']"
        echo "    ports:"
        echo "    - containerPort: 8099"
        echo "      name: cube-transfer"
        echo "    - containerPort: 8098"
        echo "      name: cube-http"
    } > transfer.yaml
    echo "cube.yaml written to ./cube.yaml"
    echo "transfer.yaml written to ./transfer.yaml"
    return 0
}

function generate_fileserver_yaml() 
{
    check_tools sed
    check_files fileserver.yaml.template
    if [ $# -ne 3 ]; then
        echo "Invalid argument to function generate_fileserver_yaml"
        return -1
    else
        hdfs_address=$1
        hdfs_ugi=$2
        dataset_path=$3
        sed -e "s#<$ HDFS_ADDRESS $>#$hdfs_address#g" \
            -e "s#<$ HDFS_UGI $>#$hdfs_ugi#g" \
            -e "s#<$ DATASET_PATH $>#$dataset_path#g" \
            fileserver.yaml.template > fileserver.yaml
        echo "File server yaml written to fileserver.yaml"
    fi  
    return 0
}

function generate_yaml()
{
    check_tools sed
    check_files fleet-ctr.yaml.template
    if [ $# -ne 11 ]; then
        echo "Invalid argument to function generate_yaml"
        return -1
    else
        pserver_num=$1
        total_trainer_num=$2
        slave_trainer_num=$((total_trainer_num))
        let total_pod_num=${total_trainer_num}+${pserver_num}
        cpu_num=$3
        mem=$4
        data_path=$5
        hdfs_address=$6
        hdfs_ugi=$7
        start_date_hr=$8
        end_date_hr=$9
        sparse_dim=${10}
        dataset_path=${11}

        sed -e "s#<$ PSERVER_NUM $>#$pserver_num#g" \
            -e "s#<$ TRAINER_NUM $>#$total_trainer_num#g" \
            -e "s#<$ SLAVE_TRAINER_NUM $>#$slave_trainer_num#g" \
            -e "s#<$ CPU_NUM $>#$cpu_num#g" \
            -e "s#<$ MEMORY $>#$mem#g" \
            -e "s#<$ DATASET_PATH $>#$dataset_path#g" \
            -e "s#<$ SPARSE_DIM $>#$sparse_dim#g" \
            -e "s#<$ HDFS_ADDRESS $>#$hdfs_address#g" \
            -e "s#<$ HDFS_UGI $>#$hdfs_ugi#g" \
            -e "s#<$ START_DATE_HR $>#$start_date_hr#g" \
            -e "s#<$ END_DATE_HR $>#$end_date_hr#g" \
            -e "s#<$ TOTAL_POD_NUM $>#$total_pod_num#g" \
            fleet-ctr.yaml.template > fleet-ctr.yaml
        echo "Main yaml written to fleet-ctr.yaml"
    fi
    return 0
}

function upload_slot_conf()
{
    check_tools kubectl curl
    if [ $# -ne 1 ]; then
        die "upload_slot_conf: Slot conf file not specified"
    fi
    check_files $1
    echo "start file-server pod"
    start_fileserver
    for number in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
        FILESERVER_IP=`kubectl get services | grep 'file-server' | awk '{print $4}'`
        echo "searching file-server external IP, wait a moment."
        if [ "${FILESERVER_IP}" == "<pending>" ]; then
            sleep 10
        else
            break 
        fi
    done
    if [ "${FILESERVER_IP}" == "<pending>" ]; then
        echo "error in K8S cluster, cannot continue. Aborted"
        return 1
    fi
    
    FILESERVER_IP=`kubectl get services | grep 'file-server' | awk '{print $4}'`
    
    FILESERVER_PORT=`kubectl get services | grep 'file-server' | awk '{print $5}' | awk -F':' '{print $2}' | awk -F',' '{print $2}'`
    if [ "${file##*.}"x = "txt"x ];
    then
        echo "slot file suffix must be '.txt'"
    fi
    echo "curl --upload-file $1 $FILESERVER_IP:$FILESERVER_PORT"
    curl --upload-file $1 $FILESERVER_IP:$FILESERVER_PORT
    if [ $? == 0 ]; then
        echo "File $1 uploaded to $FILESERVER_IP:$FILESERVER_PORT/slot.conf"
    fi
    return 0
}

function config_resource()
{
    echo "CPU=$CPU MEM=$MEM CUBE=$CUBE TRAINER=$TRAINER PSERVER=$PSERVER "\
         "CUBE=$CUBE DATA_PATH=$DATA_PATH SLOT_CONF=$SLOT_CONF VERBOSE=$VERBOSE "\
         "HDFS_ADDRESS=$HDFS_ADDRESS HDFS_UGI=$HDFS_UGI START_DATE_HR=$START_DATE_HR END_DATE_HR=$END_DATE_HR "\
         "SPARSE_DIM=$SPARSE_DIM DATASET_PATH=$DATASET_PATH "
    generate_cube_yaml $CUBE || die "config_resource: generate_cube_yaml failed"
    generate_fileserver_yaml $HDFS_ADDRESS $HDFS_UGI $DATASET_PATH || die "config_resource: generate_fileserver_yaml failed"
    generate_yaml $PSERVER $TRAINER $CPU $MEM $DATA_PATH $HDFS_ADDRESS $HDFS_UGI $START_DATE_HR $END_DATE_HR $SPARSE_DIM $DATASET_PATH || die "config_resource: generate_yaml failed"
    upload_slot_conf $SLOT_CONF || die "config_resource: upload_slot_conf failed"
    return 0
}

function log()
{
    echo "Trainer 0 Log:"
    kubectl logs fleet-ctr-demo-trainer-0 | grep __main__ > train.log
    if [ -f train.log ]; then
        tail -n 20 train.log
    else
        echo "Trainer Log Has not been generated"
    fi
    echo ""
    echo "File Server Log:"
    file_server_pod=$(kubectl get po | grep file-server | awk {'print $1'})
    kubectl logs ${file_server_pod} | grep __main__ > file-server.log
    if [ -f file-server.log ]; then
        tail -n 20 file-server.log
    else
        echo "File Server Log Has not been generated"
    fi
    echo ""
    echo "Cube Transfer Log:"
    kubectl logs cube-transfer | grep "all reload ok" > cube-transfer.log
    if [ -f cube-transfer.log ]; then
        tail -n 20 cube-transfer.log
    else
        echo "Cube Transfer Log Has not been generated"
    fi
    echo ""
    echo "Padddle Serving Log:"
    serving_pod=$(kubectl get po | grep paddleserving | awk {'print $1'})
    kubectl logs ${serving_pod} | grep __INFO__ > paddleserving.log
    if [ -f paddleserving.log ]; then
        tail -n 20 paddleserving.log
    else
        echo "PaddleServing Log Has not been generated"
    fi
}

datafile_config()
{
    source $DATA_CONF_PATH
}

function apply()
{
    echo "Waiting for pod..."
    check_tools kubectl 
    install_volcano
    kubectl get pod | grep cube | awk {'print $1'} | xargs kubectl delete pod >/dev/null 2>&1
    kubectl get pod | grep paddleserving | awk {'print $1'} | xargs kubectl delete pod >/dev/null 2>&1    
    kubectl apply -f cube.yaml
    kubectl apply -f transfer.yaml
    kubectl apply -f pdserving.yaml

    kubectl get jobs.batch.volcano.sh | grep fleet-ctr-demo
    if [ $? == 0 ]; then
        kubectl delete jobs.batch.volcano.sh fleet-ctr-demo
    fi
    kubectl apply -f fleet-ctr.yaml
    python3 listen.py &
    echo "waiting for mlflow..."
    python3 service.py  
    return
}

###############################################################################
# Main logic begin
###############################################################################

CMD=""
CPU=2
MEM=4
CUBE=2
TRAINER=2
PSERVER=2
DATA_PATH="/app"
SLOT_CONF="./slot.conf"
VERBOSE=0
DATA_CONF_PATH="./data.config"
source $DATA_CONF_PATH

# Parse arguments
TEMP=`getopt -n elastic-control -o crahu:m:t:p:b:f:s:v:l --longoption config_client,config_resource,apply,help,cpu:,mem:,trainer:,pserver:,cube:,datafile:,slot_conf:,verbose,log  -- "$@"`

# Die if they fat finger arguments, this program will be run as root
[ $? = 0 ] || die "Error parsing arguments. Try $0 --help"

eval set -- "$TEMP"
while true; do
    case $1 in
        -c|--config_client)
            CMD="config_client"; shift; continue
            ;;
        -r|--config_resource)
            CMD="config_resource"; shift; continue
            ;;
        -a|--apply)
            CMD="apply"; shift; continue
            ;;
        -h|--help)
            help
            exit 0
            ;;
        -l|--log)
            log; shift;
            exit 0
            ;;
        -u|--cpu)
            CPU="$2"; shift; shift; continue
            ;;
        -m|--mem)
            MEM="$2"; shift; shift; continue
            ;;
        -t|--trainer)
            TRAINER="$2"; shift; shift; continue
            ;;
        -p|--pserver)
            PSERVER="$2"; shift; shift; continue
            ;;
        -b|--cube)
            CUBE="$2"; shift; shift; continue
            ;;
        -f|--datafile)
            DATA_CONF_PATH="$2"; datafile_config ; shift; shift; continue
            ;;
        -s|--slot_conf)
            SLOT_CONF="$2"; shift; shift; continue
            ;;
        -v|--verbose)
            VERBOSE=1; shift; continue
            ;;
        --)
            # no more arguments to parse
            break
            ;;
        *)
            printf "Unknown option %s\n" "$1"
            exit 1
            ;;
    esac
done

if [ $CPU -lt 1 ] || [ $CPU -gt 4 ]; then
    die "Invalid CPU Num, should be greater than 0 and less than 5."
fi

if [ $MEM -lt 1 ] || [ $MEM -gt 4 ]; then
    die "Invalid MEM Num, should be greater than 0 and less than 5."
fi

if [ $PSERVER -lt 1] || [ $PSERVER -gt 9]; then
    die "Invalid PSERVER Num, should be greater than 0 and less than 10."
fi

if [ $TRAINER -lt 1] || [ $TRAINER -gt 9]; then
    die "Invalid TRAINER Num, should be greater than 0 and less than 10."
fi

if [ $CUBE -lt 0] && [ $CUBE -gt 9 ]; then
    die "Invalid CUBE Num, should be greater than 0 and less than 10."
fi



case $CMD in
config_resource)
    config_resource
    ;;
config_client)
    config_client
    ;;
apply)
    apply
    ;;
status)
    status
    ;;
*)
    help
    ;;
esac
