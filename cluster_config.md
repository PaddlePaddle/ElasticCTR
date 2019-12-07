### 1 创建k8s集群

请参考
[百度智能云CCE容器引擎帮助文档-创建集群](https://cloud.baidu.com/doc/CCE/s/zjxpoqohb)，在百度智能云上建立一个集群，节点配置需要满足如下要求

- CPU核数 \> 4

申请容器引擎示例:

![image](https://github.com/PaddlePaddle/Serving/raw/master/doc/elastic_ctr/ctr_node.png)

创建完成后，即可参考[百度智能云CCE容器引擎帮助文档-查看集群](https://cloud.baidu.com/doc/CCE/GettingStarted.html#.E6.9F.A5.E7.9C.8B.E9.9B.86.E7.BE.A4)，查看刚刚申请的集群信息。

### 2 如何操作集群

集群的操作可以通过百度云web或者通过kubectl工具进行，推荐用kubectl工具。

mac和linux用户安装kubectl工具可以参考以下步骤：

1.下载最新版本的kubectl
```bash
curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/darwin/amd64/kubectl"
```
2.为kubectl添加执行权限
```bash
chmod +x ./kubectl
```
3.将刚下载好的可执行文件移动到环境变量路径下
```bash
sudo mv ./kubectl /usr/local/bin/kubectl
```
4.检测安装是否成功
```bash
kubectl version
```

\* 注意： 本操作指南给出的操作步骤都是基于linux操作环境的。

-   安装好kubectl后，我们还要配置kubectl，下载集群凭证。集群凭证可以在百度云控制台查看，如下图所示
![config](https://github.com/suoych/WebChat/raw/master/d9d953129f4a27d8ec728d0a8.png)
在集群界面下载集群配置文件，放在kubectl的默认配置路径（请检查\~/.kube目录是否存在，若没有请创建）

```bash
$ mv kubectl.conf  ~/.kube/config
```

-   配置完成后，您即可以使用kubectl从本地计算机访问Kubernetes集群(注：请确保您的机器上没有配置网络代理)

```bash
$ kubectl get node
```


### 3 设置访问权限

建立分布式任务需要pod间有API互相访问的权限，可以按如下步骤

```bash
$ kubectl create rolebinding default-view --clusterrole=view --serviceaccount=default:default --namespace=default
```

注意： --namespace 指定的default 为创建集群时候的名称

### 4 安装Volcano

我们使用volcano作为训练阶段的批量任务管理工具。关于volcano的详细信息，请参考[官方网站](https://volcano.sh/)的Documentation。

执行以下命令安装volcano到k8s集群：

```bash
$ kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/master/installer/volcano-development.yaml
```

![image](https://github.com/PaddlePaddle/Serving/raw/master/doc/elastic_ctr/ctr_volcano_install.png)


