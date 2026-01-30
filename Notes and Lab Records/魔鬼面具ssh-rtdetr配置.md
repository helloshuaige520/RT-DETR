查看pytorch版本：
![1762482774383](C:\Users\cqq\AppData\Roaming\Typora\typora-user-images\1762482774383.png)

选择相应版本

![1762482708866](C:\Users\cqq\AppData\Roaming\Typora\typora-user-images\1762482708866.png)

配置数据集：
![1762482875331](C:\Users\cqq\AppData\Roaming\Typora\typora-user-images\1762482875331.png)

解压从算力控制台上传的rtdetr文件：
![1762482961829](C:\Users\cqq\AppData\Roaming\Typora\typora-user-images\1762482961829.png)

上面的命令有问题，正确的应该是：unzip RTDETR-main.zip -d RTDETR-main

文件传至数据盘可持久保存：
![1762483072743](C:\Users\cqq\AppData\Roaming\Typora\typora-user-images\1762483072743.png)

cd进入项目目录，然后激活conda虚拟环境：

```shell
conda env list
conda activate envname
```

右键选择dataset里面的yaml配置文件选择“复制路径”，粘贴到train.py中的	data='  '中

接着可以跑代码   python train.py  

生成的pt文件在runs/exp2

- 这里要注意的是，生成的实验结果数据exp文件，会根据实验次数默认排序，比如进行的是第三次实验，文件夹就是exp3，这个适合detect.py里面的参数以及其他涉及到实验结果的代码需要调整

其中weight文件里

**best.pt**：表示训练过程中性能最好的模型权重，通常是在验证集上表现最好的那个模型。

**last.pt**：表示最后训练完的模型权重，是训练完成时的最新权重。



