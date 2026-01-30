import torch
import torch.nn as nn
import torchvision.models as models

# 1. 准备模型 (这里用 ResNet 模拟你的 RT-DETR backbone，逻辑一样)
# 在实际项目中，这里加载你的 RT-DETR: model = RTDETR('rtdetr-l.pt')
model = models.resnet18(pretrained=False) 
model.eval() # 关键！必须切到 eval 模式，固化 BN 层的均值和方差，并禁用 Dropout

# 2. 创建一个“假数据” (Dummy Input)
# 格式：[Batch, Channel, Height, Width]
dummy_input = torch.randn(1, 3, 640, 640)

# 3. 定义动态轴 (Dynamic Axes) —— 面试加分项！
# 告诉 ONNX：我的 Batch Size 和 图片长宽 是可变的，不要写死。
dynamic_axes = {
    'input': {0: 'batch_size', 2: 'height', 3: 'width'},
    'output': {0: 'batch_size'}
}

# 4. 导出 ONNX
output_file = "model_dynamic.onnx"
print(f"正在导出 {output_file} ...")

torch.onnx.export(
    model,                      # 模型实例
    dummy_input,                # 假输入，用来跑一次前向传播追踪计算图
    output_file,                # 输出文件名
    export_params=True,         # 是否打包权重
    opset_version=11,           # 算子集版本 (11 或 13 最通用，面试若问选几就说11/13)
    do_constant_folding=True,   # 优化常量折叠
    input_names=['input'],      # 输入节点名 (部署时要对齐)
    output_names=['output'],    # 输出节点名
    dynamic_axes=dynamic_axes   # 启用动态维度
)

print("导出成功！可以使用 Netron.app 打开查看结构。")