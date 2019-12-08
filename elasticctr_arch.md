
# ElasticCTR整体架构

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
