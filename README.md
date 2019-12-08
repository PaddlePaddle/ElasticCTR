<img src='docs/source/_static/FL-logo.png' width = "400" height = "160">

# ElasticCTR

ElasticCTR是百度云分布式训练CTR预估任务和Serving流程一键部署的方案，用户只需配置数据源、样本格式即可完成一系列的训练与预测任务

* [1. 总体概览](#head1)
* [2. 配置集群](#head2)
* [3. 一键部署教程](#head3)
* [4. 训练进度追踪](#head4)
* [5. 预测服务](#head5)

## <span id='head1'>1. 总体概览</span>

本项目提供了端到端的CTR训练和二次开发的解决方案，主要特点如下：

1.快速部署

ElasticCTR当前提供的方案是基于百度云的Kubernetes集群进行部署，用户可以很容易扩展到其他原生的Kubernetes环境运行ElasticCTR。
  
2.高性能

ElasticCTR采用PaddlePaddle提供的全异步分布式训练方式，在保证模型训练效果的前提下，近乎线性的扩展能力可以大幅度节省训练资源。在线服务方面，ElasticCTR采用Paddle Serving中高吞吐、低延迟的稀疏参数预估引擎，高并发条件下是常见开源组件吞吐量的10倍以上。

3.可定制

用户可以通过统一的配置文件，修改训练中的训练方式和基本配置，包括在离线训练方式、训练过程可视化指标、HDFS上的存储配置等。除了通过修改统一配置文件进行训练任务配置外，ElasticCTR采用全开源软件栈，方便用户进行快速的二次开发和改造。底层的Kubernetes、Volcano可以轻松实现对上层任务的灵活调度策略；基于PaddlePaddle的灵活组网能力、飞桨的分布式训练引擎Fleet和远程预估服务Paddle Serving，用户可以对训练模型、并行训练的模式、远程预估服务进行快速迭代；MLFlow提供的训练任务可视化能力，用户可以快速增加系统监控需要的各种指标。


本方案整体结构请参照这篇文章 [ElasticCTR架构](elasticctr_arch.md)

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






