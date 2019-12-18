# AWS搭建k8s集群

本文档旨在介绍如何在aws上搭建k8s集群

* [1. 流程概述](#head1)
* [2. 购买跳板机](#head2)
* [3. 部署集群](#head3)

## <span id='head1'>1. 流程概述</span>

在aws上搭建k8s集群主要有以下两个步骤：

1.购买跳板机

首先需要购买一个ec2实例作为跳板机来控制k8s集群，这个实例不需要很高的配置
  
2.部署集群

用上一步购买的跳板机创建集群，集群的配置可以自行调整

下面对每一步进行详细介绍。

## <span id='head2'>2. 购买跳板机</span>

用户可以在EC2控制台购买想要的实例作为跳板机。

具体的操作如下：
1. 打开 Amazon EC2 控制台，从控制台控制面板中，点击启动实例按钮。
![run_instance.png](https://github.com/suoych/WebChat/raw/master/run_instance.png)
2. 选择合适的AMI，建议选用Amazon Linux 2 AMI。
![choose_AMI.png](https://github.com/suoych/WebChat/raw/master/choose_AMI.png)
3. 选择实例类型，建议选用默认的t2.micro，选好后点击审核和启动
![choose_instance_type.png](https://github.com/suoych/WebChat/raw/master/choose_instance_type.png)
4. 在审核界面，在核查实例启动页面上的安全组栏中点击编辑安全组，然后在配置安全组界面中点击选择一个现有的安全组，点击名称为default的安全组，再点击审核和启动。
![review_instance.png](https://github.com/suoych/WebChat/raw/master/review_instance.png)
![select_security_group.png](https://github.com/suoych/WebChat/raw/master/select_security_group.png)
5. 在审核界面点击启动，在弹出的密钥对窗口中选择创建新密钥对，自定义密钥名称后下载密钥对，请一定保存好密钥对文件，因为丢失后无法再次下载。以上操作完成后点击启动实例即可完成跳板机购买。
![create_key.png](https://github.com/suoych/WebChat/raw/master/create_key.png)


请注意：密钥对文件下载之后请修改权限为400。

## <span id='head3'>3. 部署集群</span>

在上一步购买的实例启动后会显示公网ip和DNS，连接到实例进行部署，连接需要用到刚才下载的密钥对文件(后缀为.pem)，连接指令如下：

```bash
ssh -i ec2key.pem ec2-user@12.23.34.123
```
或
```bash
ssh -i ec2key.pem ec2-user@ec2-12-23-34-123.us-west-2.compute.amazonaws.com
```

连接到跳板机后，需要安装一系列操控组件，具体如下：
1. 安装pip
```bash
sudo yum -y install python-pip
```
2. 安装或升级 AWS CLI
```bash
sudo pip install --upgrade awscli
```
3. 安装 eksctl
```bash
curl --silent \
--location "https://github.com/weaveworks/eksctl/releases/download/latest_release/eksctl_$(uname -s)_amd64.tar.gz" \
| tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```
4. 安装 kubectl
```bash
curl -o kubectl https://amazon-eks.s3-us-west-2.amazonaws.com/1.11.5/2018-12-06/bin/linux/amd64/kubectl
chmod +x ./kubectl
mkdir -p $HOME/bin && cp ./kubectl $HOME/bin/kubectl && export PATH=$HOME/bin:$PATH
```
5. 安装 aws-iam-authenticator
```bash
curl -o aws-iam-authenticator https://amazon-eks.s3-us-west-2.amazonaws.com/1.11.5/2018-12-06/bin/linux/amd64/aws-iam-authenticator
chmod +x aws-iam-authenticator
cp ./aws-iam-authenticator $HOME/bin/aws-iam-authenticator && export PATH=$HOME/bin:$PATH
```
6. 安装 ksonnet
```bash
export KS_VER=0.13.1
export KS_PKG=ks_${KS_VER}_linux_amd64
wget -O /tmp/${KS_PKG}.tar.gz https://github.com/ksonnet/ksonnet/releases/download/v${KS_VER}/${KS_PKG}.tar.gz
mkdir -p ${HOME}/bin
tar -xvf /tmp/$KS_PKG.tar.gz -C ${HOME}/bin
sudo mv ${HOME}/bin/$KS_PKG/ks /usr/local/bin
```

安装好这些组件后，用户可以购买集群并部署，指令如下：
```bash
eksctl create cluster paddle-cluster \
                      --version 1.13 \
                      --nodes 2 \
                      --node-type=m5.2xlarge \
                      --timeout=40m \
                      --ssh-access \
                      --ssh-public-key ec2.key \
                      --region us-west-2 \
                      --auto-kubeconfig
```
其中：

**--version** 指k8s版本，目前aws支持1.12, 1.13 和 1.14

**--nodes** 指节点数量

**--node-type** 指节点实例型号，用户可以挑选自己喜欢的实例套餐

**--ssh-public-key** 用户可以使用之前购买跳板机时定义的密钥名称

**--region** 指节点所在地区

部署集群所需时间较长，请耐心等待，当部署成功后，用户可以测试集群，具体方法如下：

1. 输入以下指令查看节点信息：
```bash
kubectl get nodes -o wide
```
2. 验证集群是否处于活动状态：
```bash
aws eks --region <region> describe-cluster --name <cluster-name> --query cluster.status
```
应看到如下输出：
```
"ACTIVE"
```
3. 如果在同一跳板机中具有多个集群设置，请验证 kubectl 上下文：
```bash
kubectl config get-contexts
```
如果未按预期设置该上下文，请使用以下命令修复此问题：
```bash
aws eks --region <region> update-kubeconfig --name <cluster-name>
```
以上是AWS搭建k8s集群的全部步骤，用户接下来可以再自行在aws上搭建hdfs，并在跳板机上部署elastic ctr2.0
