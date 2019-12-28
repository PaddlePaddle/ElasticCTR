# 华为云搭建k8s集群

本文档旨在介绍如何在华为云上搭建k8s集群，以便部署ElasticCTR。

* [1. 流程概述](#head1)
* [2. 购买集群](#head2)
* [3. 定义负载均衡](#head2)
* [4. 上传镜像](#head3)

## <span id='head1'>1. 流程概述</span>

在华为云上搭建k8s集群主要有以下三个步骤：

1.购买集群

首先需要登录到华为云的cce控制台，购买合适配置的集群
 
2.定义负载均衡

用上一步购买的跳板机创建集群，集群的配置可以自行调整

3. 上传镜像

华为云提供了镜像仓库的服务，我们可以将所需的镜像上传到仓库，以后拉取镜像的速度会变快

下面对每一步进行详细介绍。

## <span id='head2'>2. 购买集群</span>

用户登录到华为云的cce控制台购买k8s集群，具体的操作如下：

1. 打开华为云cce控制台，从控制台控制面板中，点击购买Kubernetes集群，在购买混合集群界面的服务选型项下设置集群信息，总体配置等。
![huawei_cce_choose_service.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_choose_service.png)

2. 集群信息设置好后，点击下一步：创建节点，在创建节点项下设置节点配置。
![huawei_cce_create_node.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_create_node.png)
![huawei_cce_create_node_configure.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_create_node_configure.png)
![huawei_cce_create_node_configure_1.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_create_node_configure_1.png)

3. 节点设置完成后，在安装插件项的高级功能插件下选择volcano，然后可以确认配置，完成支付。
![huawei_cce_plugin.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_plugin.png)

## <span id='head3'>3. 定义负载均衡</span>

由于华为云对于负载均衡有限制，建议参考[华为云负载均衡](https://support.huaweicloud.com/usermanual-cce/cce_01_0014.html)，修改 fileserver.yaml.template和pdserving.yaml 关于 Service定义的metadata，参见下图
![huawei_cce_load_balancer.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_load_balancer.png)


## <span id='head4'>4. 上传镜像</span>

注：本步骤为可选操作，如果经费充足可以不做这一步。
点击镜像仓库，按照提示登录仓库，将指令复制到节点终端上执行，如下图所示：
![huawei_cce_image_repo.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_image_repo.png)

随后按照提示将elastic ctr所需的镜像上传到仓库中
![huawei_cce_image_upload.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_image_upload.png)

完成操作后可以看到效果如下：
![huawei_cce_image_upload_success.png](https://github.com/suoych/WebChat/raw/master/huawei_cce_image_upload_success.png)

至此，我们完成了华为云搭建k8s的流程，用户可以自行搭建hdfs，部署elastic ctr。




