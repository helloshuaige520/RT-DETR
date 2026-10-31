import warnings, os
# os.environ["CUDA_VISIBLE_DEVICES"]="-1"    # 代表用cpu训练 不推荐！没意义！ 而且有些模块不能在cpu上跑
# os.environ["CUDA_VISIBLE_DEVICES"]="0"     # 代表用第一张卡进行训练  0：第一张卡 1：第二张卡
# 多卡训练参考<使用教程.md>下方常见错误和解决方案
warnings.filterwarnings('ignore')
from ultralytics import RTDETR

# 深度学习炼丹必备必看必须知道的小技巧！https://www.bilibili.com/video/BV1q3SZYsExc/
# 整合多个创新点的B站视频链接:
# 1. [YOLOV8-不会把多个改进整合到一个yaml配置文件里面？那来看看这个吧！从简到难手把手带你整合三个yaml](https://www.bilibili.com/video/BV15H4y1Y7a2/)
# 2. [细谈目标检测中的小目标检测头和大目标检测检测头，并教懂你怎么加微小目标、极大目标检测头！](https://www.bilibili.com/video/BV1jkDWYFEwx/)
# 3. [不会看YOLO的模型yaml配置文件？那你还怎么整合多个配置文件！](https://www.bilibili.com/video/BV1oiBRYnEEw/)
# 4. [不会把多个创新点整合到一个yaml配置文件里面？那来看看这个吧！手把手来你整合创新点！](https://www.bilibili.com/video/BV1DUBRYGE3b/)
# 更多问题解答请看使用说明.md下方<常见疑问>

# 现版本中保存模型会比之前的大一倍，原因是因为之前保存模型的格式是fp16，但是fp16可能会导致部分模型在训练中精度正常
# 但是在val.py的时候精度为0，所以统一改成fp32，原则上没影响，只是存储的位数变多了。

if __name__ == '__main__':
    model = RTDETR('/home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/ultralytics/cfg/models/rt-detr/rtdetr-SPAFM.yaml')
    model.train(#data='/home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/dataset/cityperson.yaml',
                data='/home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/dataset/data.yaml',
                cache=False,
                imgsz=640,
                epochs=300, 
                batch=4, # 先把batch从1提高到2，能明显减少每轮迭代数；如显存溢出再改回1
                workers=4, # 训练盘IO稳定后恢复并行读图，避免GPU等数据
                amp=False, # RT-DETR + DCNv4 自定义CUDA算子在AMP下容易触发异步CUDA错误
                # device='0,1', # 指定显卡和多卡训练参考<使用教程.md>下方常见错误和解决方案
                 # resume='/home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/runs/train/rtdetr-visdrone2019-SPAFM/weights/last.pt',  # 从零训练；中断后需续训时取消注释并指向该 run 的 last.pt
                project='runs/train',
                name='rtdetr-visdrone2019-SPAFM',
                )
