# ELASTIC CTR 2.0

Elastic CTR 2.0是百度云分布式训练CTR预估任务和Serving流程一键部署的方案，用户只需配置数据源、样本格式即可完成一系列的训练与预测任务

* [1. 总体概览](#head1)
* [2. 配置集群](#head2)
* [3. 一键部署教程](#head3)
* [4. 训练进度追踪](#head4)
* [5. 预测服务](#head5)

## <span id='head1'>1. 总体概览</span>

本项目提供了端到端的CTR训练和二次开发的解决方案，主要特点如下：

1.快速部署

整体方案在k8s环境一键部署，可快速搭建与验证效果
  
2.高性能

基于Paddle Fleet API的大规模分布式高速训练，工业级稀疏参数Serving组件，高并发条件下单位时间吞吐总量是redis的13倍，训练资源弹性伸缩

3.可定制

用户可以自定义配置文件，支持在线训练与离线训练以及训练数据可视化，支持在HDFS上存储数据。Elastic CTR使用完全开源的软件栈，用户可以进行二次开发


本方案整体结构如下图所示：
![elastic.png](https://github.com/suoych/WebChat/raw/master/overview_v2.png)
其中各个模块的介绍如下：
- Client: CTR预估任务的客户端，训练前用户可以上传自定义的配置文件，预测时可以发起预测请求
- file server: 接收用户上传的配置文件，存储模型供Paddle Serving和Cube使用。
- trainer/pserver: 训练环节采用PaddlePaddle parameter server模式，对应trainer和pserver角色。分布式训练使用volcano做批量任务管理工具。
- MLFlow: 训练任务的可视化模块，用户可以直观地查看训练情况。
- HDFS:  用于用户存储数据。训练完成后产出的模型文件，也会在HDFS存储。
- cube-transfer: 负责监控上游训练任务产出的模型文件，有新的模型产出便拉取到本地，并调用cube-builder构建cube字典文件；通知cube-agent节点拉取最新的字典文件，并维护各个cube-server上版本一致性。
- cube-builder: 负责将训练作业产出的模型文件转换成可以被cube-server加载的字典文件。字典文件具有特定的数据结构，针对尺寸和内存中访问做了高度优化。
- Cube-Server: 提供分片kv读写能力的服务节点。
- Cube-agent: 与cube-server同机部署，接收cube-transfer下发的字典文件更新命令，拉取数据到本地，通知cube-server进行更新。
- Paddle Serving: 加载CTR预估任务模型ProgramDesc和dense参数，提供预测服务。

以上组件串联完成从训练到预测部署的所有流程。本项目所提供的一键部署脚本elastic-control.sh可一键部署上述所有组件。用户可以参考本部署方案，将基于PaddlePaddle的分布式训练和Serving应用到业务环境。

## <span id='head2'>2. 配置集群</span>

运行本方案前，需要用户已经搭建好k8s集群，并安装好volcano组件。k8s环境部署比较复杂，本文不涉及。百度智能云CCE容器引擎申请后即可使用，百度云上创建k8s的方法用户可以参考这篇文档[百度云创建k8s教程及使用指南](cluster_config.md)。


## <span id='head3'>3. 一键部署教程</span>

您可以使用我们提供的脚本elastic-control.sh来完成部署，脚本的使用方式如下：
```
bash elastic-control.sh [COMMAND] [OPTIONS]
```
其中可选的命令(COMMAND)如下：
- **-c|--config_client**    检索客户端二进制文件用于发送预测服务请求并接收预测结果
- **-r|--config_resource**  定义训练配置
- **-a|--apply**            应用配置并启动训练
- **-l|--log**              打印训练状态，请确保您已经启动了训练

在定义训练配置时，您需要添加附加选项(OPTIONS)来指定配置的资源，可选的配置如下：
- **-u|--cpu**              每个训练节点的CPU核心数
- **-m|--mem**              每个节点的内存容量
- **-t|--trainer**          trainer节点的数量
- **-p|--pserver**          parameter-server节点的数量
- **-b|--cube**             cube分片数
- **-hd|--hdfs_address**    存储数据文件的HDFS地址

注意：您的数据文件的格式应为以下示例格式：
```
$show $click $feasign0:$slot0 $feasign1:$slot1 $feasign2:$slot2......
```
举例如下：
```
1 0 17241709254077376921:0 132683728328325035:1 9179429492816205016:2 12045056225382541705:3
```
    
- **-f|--datafile**         数据路径文件，需要指明HDFS地址并指定起始与截止日期（截止日期可选）
- **-s|--slot_conf**        特征槽位配置文件，请注意文件后缀必须为'.txt'

脚本的使用示例如下：
```
bash elastic-control.sh -r -u 4 -m 20 -t 2 -p 2 -b 5 -s slot.conf -f data.config
bash elastic-control.sh -a
bash elastic-control.sh -l
bash elastic-control.sh -c
```

## <span id='head4'>4. 训练进度追踪</span>
我们提供了两种方法让用户可以观察训练的进度，具体方式如下：

1.命令行查看

在训练过程中，用户可以随时输入以下命令，将Trainer0和file server的状态日志打印到标准输出上以便查看
```bash
bash elastic-control.sh -l
```
2.mlflow可视化界面

注意：该方法要求客户端机器可以使用浏览器

在训练过程中，用户可以输入以下指令后用浏览器访问127.0.0.1:8111查看训练情况界面
```bash
kubectl port-forward fleet-ctr-demo-trainer-0 8111:8111
```
可以看到页面显示效果如下所示：
![elastic.png](https://github.com/suoych/WebChat/raw/master/MacHi%202019-11-25%2014-19-30.png)
![dashboard.png](https://github.com/suoych/WebChat/raw/master/MacHi%202019-11-25%2014-18-32.png)

## <span id='head5'>5. 预测服务</span>
用户可以输入以下指令查看file server日志：
```bash
bash elastic-control.sh -l
```
当发现有模型产出后，可以进行预测，预测的方法是输入以下命令
```bash
bash elastic-control.sh -c
```
并按照屏幕上打出的提示继续执行即可进行预测，结果会打印在标准输出
![infer_help.png](https://github.com/suoych/WebChat/raw/master/infer_help.png)






