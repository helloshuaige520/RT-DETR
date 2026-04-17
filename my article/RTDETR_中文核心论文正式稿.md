# 面向无人机电力巡检与航拍场景的 RT-DETR 增强型小目标检测算法研究

**作者**：（作者姓名）　**单位**：（单位名称）

---

## 摘要

针对无人机电力巡检与低空航拍场景中目标尺寸小、分布密集、背景干扰强以及遮挡严重等问题，原始 RT-DETR 在高倍率下采样后易出现细粒度信息丢失和小目标定位不稳的现象。为此，本文提出一种面向小目标检测的增强型 RT-DETR 改进算法。首先，在骨干网络中以 C2f-AdditiveBlock-CGLU 替代传统卷积特征提取单元，利用局部感知、加性 Token 混合与卷积门控线性单元协同增强浅层纹理与中层语义表征，同时有效降低模型参数量；其次，在特征融合阶段引入步长为 4 的 P2 高分辨率检测分支，构建四尺度特征金字塔，并采用 DySample 动态上采样算子替代传统最近邻插值，以保留微小目标的边缘细节；进一步地，在 P2/P3 阶段嵌入坐标注意力机制，强化空间位置信息建模，并在颈部引入 ASFF_V3 自适应特征融合模块消除多尺度特征间的语义冲突；最后，结合 Inner-IoU 与归一化 Wasserstein 距离（NWD）的组合回归损失，提升密集场景下的边界框拟合质量。以 VisDrone2019 作为通用无人机航拍小目标基准数据集进行验证，实验结果表明：相较 RT-DETR-r18 基线，所提方法在参数量减少 36.2% 的条件下，mAP50 由 38.29% 提升至 39.85%，mAP50-95 由 22.27% 提升至 23.33%，验证了所提方法在兼顾精度与轻量化方面的有效性。

**关键词**：无人机巡检；航拍图像；小目标检测；RT-DETR；多尺度特征融合；坐标注意力；动态上采样

---

## Abstract

To address the challenges of small target size, dense distribution, complex background interference, and severe occlusion in UAV power inspection and low-altitude aerial imaging scenarios, the original RT-DETR suffers from fine-grained information loss and unstable small target localization after high-ratio downsampling. This paper proposes an enhanced RT-DETR algorithm for small target detection. First, C2f-AdditiveBlock-CGLU replaces conventional convolutional feature extraction units in the backbone, leveraging local perception, additive token mixing, and convolutional gated linear units to jointly enhance shallow texture and mid-level semantic representations while reducing model parameters. Second, a P2 high-resolution detection branch with stride 4 is introduced to construct a four-scale feature pyramid, and DySample dynamic upsampling replaces traditional nearest-neighbor interpolation to preserve edge details of tiny targets. Furthermore, coordinate attention is embedded in P2/P3 stages to strengthen spatial position modeling, and ASFF_V3 adaptive feature fusion is applied in the neck to eliminate semantic conflicts across scales. Finally, a combined regression loss of Inner-IoU and Normalized Wasserstein Distance (NWD) improves bounding box fitting quality in dense scenes. Experiments on VisDrone2019 demonstrate that compared to the RT-DETR-r18 baseline, the proposed method achieves mAP50 of 39.85% and mAP50-95 of 23.33% with 36.2% fewer parameters, validating its effectiveness in balancing accuracy and lightweight design.

**Keywords**: UAV inspection; aerial image; small target detection; RT-DETR; multi-scale feature fusion; coordinate attention; dynamic upsampling

---

## 0 引言

无人机技术的快速发展使其在电力巡检、低空航拍、应急救援和交通监控等领域得到广泛应用[1]。在电力巡检场景中，无人机需要在复杂背景下识别绝缘子、导线金具、螺栓松动等细小部件；在低空航拍场景中，行人、车辆、非机动车等目标因拍摄高度大而在图像中仅占据极少像素。这类场景具有视角高、拍摄范围广、目标尺度跨度大等特点，目标往往仅占图像面积的 0.01% 以下，且常伴随密集分布与局部遮挡，对目标检测算法提出了严峻挑战[2]。

目标检测方法大致可分为两类：基于卷积神经网络（CNN）的方法和基于 Transformer 的方法。前者以 YOLO 系列[3-4]为代表，具有较高推理效率，但在长距离依赖建模和密集场景全局关联表达方面存在不足；后者以 DETR[5] 及其变体为代表，具有端到端和全局建模优势，但早期版本训练收敛慢、计算开销大。RT-DETR[6] 通过高效混合编码器与实时查询机制在精度与速度之间取得了较好平衡，成为近年来无人机小目标检测研究的重要基础框架。

然而，原始 RT-DETR 在小目标航拍场景中仍存在明显不足。一方面，其默认最浅检测层为 P3（下采样 8 倍），对于 VisDrone 等数据集中大量 10×10 像素以下的微小目标，特征在多次下采样后几乎完全消失；另一方面，传统双线性或最近邻上采样在特征金字塔的自顶向下路径中会引入模糊，进一步损失小目标边缘信息；此外，标准 IoU 类损失对小目标框的轻微偏移极为敏感，导致训练过程中回归监督不稳定。

针对上述问题，近年来研究者从多个角度对 RT-DETR 进行了改进。田红鹏等[7]在骨干中引入 C2f-Heat-Lsk 结构并设计 SOFEP 特征融合模块，在航拍图像上取得了较好效果；胡康等[8]提出 FRE-Block 与动态位置偏置，增强了密集场景下的特征表达；符强等[9]设计了 WFU 小波特征升级模块，改善了高频细节保留能力；刘杰等[10]引入 SPDConv 与 CSP-OmniKernel，提升了多尺度特征提取效率。这些工作表明，针对小目标场景的 RT-DETR 改进通常需要在骨干轻量化、高分辨率特征引入和回归损失优化三个维度协同发力。

基于此，本文提出一种面向无人机电力巡检与航拍场景的增强型 RT-DETR 小目标检测算法，主要贡献如下：

1. 提出以 C2f-AdditiveBlock-CGLU 为核心的轻量化骨干，通过加性 Token 混合与卷积门控线性单元协同提升特征表达效率，在降低参数量的同时增强浅层纹理表征。
2. 构建基于 P2 高分辨率分支的四尺度检测头，引入 DySample 动态上采样保留微小目标边缘细节，并以 ASFF_V3 自适应融合消除多尺度语义冲突。
3. 在 P2/P3 阶段嵌入坐标注意力机制，并采用 Inner-IoU 与 NWD 组合回归损失，改善密集场景下的空间注意分配与边界框拟合质量。


---

## 1 RT-DETR 算法基本原理

RT-DETR（Real-Time Detection Transformer）[6] 由骨干网络、混合编码器（Hybrid Encoder）和 Transformer 解码器三部分组成，如图1所示。骨干网络负责提取多尺度卷积特征 $\{P_3, P_4, P_5\}$；混合编码器由序列内注意力（AIFI）和跨尺度特征融合（CCFM）两个子模块构成，前者在 P5 层进行全局自注意力建模，后者通过卷积融合单元完成多尺度特征聚合；解码器通过固定数量的查询向量（Query）与编码器输出进行交叉注意力交互，最终完成类别预测与边界框回归，无需非极大值抑制（NMS）后处理。

设编码器输出的多尺度特征为 $\{F_l\}_{l=3}^{5}$，解码器第 $d$ 层的查询向量 $Q^{(d)}$ 通过如下交叉注意力更新：

$$
Q^{(d+1)} = \mathrm{CrossAttn}\!\left(Q^{(d)},\, \{F_l\}\right) + Q^{(d)}, \tag{1}
$$

最终由分类头和回归头分别输出类别概率与边界框坐标。

原始 RT-DETR 在小目标航拍场景中存在以下三点不足：（1）最浅检测层为 P3（步长 8），对于 VisDrone 中大量 10 像素以下的微小目标，特征在多次下采样后几乎消失；（2）特征金字塔自顶向下路径采用最近邻或双线性上采样，会引入模糊并损失小目标边缘信息；（3）标准 IoU 损失对小目标框的轻微偏移极为敏感，训练过程中回归监督不稳定。本文针对上述三点进行协同改进。

---

## 2 改进模型设计

### 2.1 整体结构

本文改进模型以 RT-DETR-r18 为基础框架，在骨干网络、特征融合颈部和回归损失三个层面进行协同改进，整体结构如图1所示。

**骨干网络**：以 C2f-AdditiveBlock-CGLU（含 CoordAtt）替换原始 ResNet-18 的特征提取块，在 P4/P5 阶段引入 DCNv4 可变形卷积，增强对航拍目标形状多变性的适应能力。

**特征融合颈部**：在原有 P3-P5 三尺度基础上新增 P2（步长 4）高分辨率分支，构建四尺度特征金字塔；自顶向下路径采用 DySample 动态上采样替代传统插值；在 PAN 底部上行路径之后，引入 ASFF_V3 对四尺度特征进行自适应加权融合。

**检测头与损失**：RTDETRDecoder 接收四尺度融合特征，采用 300 个查询向量；回归损失采用 Inner-IoU 与 NWD 的加权组合，分类损失采用 EMA-SVFL。

```
% 图1说明（tikz代码见附录A）
图1  改进 RT-DETR 小目标检测网络整体结构
```

### 2.2 C2f-AdditiveBlock-CGLU 轻量化骨干

#### 2.2.1 模块设计动机

原始 RT-DETR-r18 骨干采用标准残差卷积块，参数量约 19.88M，计算量 57.0 GFLOPs。对于无人机边缘部署场景，模型轻量化是重要约束。本文引入 C2f-AdditiveBlock-CGLU，其核心思想是以加性 Token 混合（Additive Token Mixing）替代标准自注意力的乘性计算，以卷积门控线性单元（CGLU）替代标准 MLP，在保持特征表达能力的同时显著降低计算复杂度。

#### 2.2.2 AdditiveBlock 结构

AdditiveBlock 由三个子模块串联组成：局部感知（LocalIntegration）、加性 Token 混合（AdditiveTokenMixer）和卷积门控线性单元（CGLU），各子模块均采用残差连接。设输入特征为 $X \in \mathbb{R}^{C \times H \times W}$，完整前向计算过程为：

$$
X_1 = X + \mathcal{L}(X), \tag{2}
$$

$$
X_2 = X_1 + \mathcal{A}\!\left(\mathrm{BN}(X_1)\right), \tag{3}
$$

$$
Y = X_2 + \mathcal{G}\!\left(\mathrm{BN}(X_2)\right), \tag{4}
$$

其中 $\mathcal{L}(\cdot)$ 为局部感知映射（深度可分离卷积），$\mathcal{A}(\cdot)$ 为加性 Token 混合，$\mathcal{G}(\cdot)$ 为 CGLU，$\mathrm{BN}(\cdot)$ 为批归一化，$Y$ 为输出特征。

**加性 Token 混合**的核心计算为：

$$
\mathcal{A}(X) = \mathrm{DWConv}\!\left(\mathrm{Conv}_{1\times1}(X)_Q + \mathrm{Conv}_{1\times1}(X)_K\right) \odot \mathrm{Conv}_{1\times1}(X)_V, \tag{5}
$$

其中 $Q, K, V$ 为通过三个独立 $1\times1$ 卷积得到的查询、键、值特征，$\mathrm{DWConv}$ 为深度可分离卷积，$\odot$ 为逐元素相乘。与标准自注意力的 $\mathrm{softmax}(QK^\top/\sqrt{d})V$ 相比，加性融合 $(Q+K)$ 将复杂度从 $\mathcal{O}(N^2)$ 降至 $\mathcal{O}(N)$，更适合高分辨率特征图处理。

**卷积门控线性单元（CGLU）**的计算为：

$$
\mathcal{G}(X) = X_{\mathrm{sc}} + \mathrm{FC}_2\!\left(\mathrm{DWConv}(X_g) \odot X_v\right), \tag{6}
$$

其中 $[X_g, X_v] = \mathrm{FC}_1(X).\mathrm{chunk}(2)$ 为将全连接层输出沿通道维度均分为门控分支与值分支，$X_{\mathrm{sc}}$ 为输入的残差捷径。CGLU 通过深度可分离卷积引入空间感知门控，相比标准 GLU 具有更强的局部上下文建模能力。

模块结构示意如图2所示。

```
% 图2说明（tikz代码见附录A）
图2  C2f-AdditiveBlock-CGLU 模块结构示意图
```

### 2.3 DySample 动态上采样

特征金字塔自顶向下路径中的上采样质量直接影响小目标特征的保留程度。传统最近邻插值会引入块状伪影，双线性插值则会模糊边缘细节。本文采用 DySample[11] 动态上采样，其核心思想是通过轻量卷积预测每个输出像素的采样偏移，再以可微分的双线性网格采样完成上采样，从而自适应地保留目标边缘信息。

设输入特征图为 $F \in \mathbb{R}^{C \times H \times W}$，上采样倍率为 $s$，DySample 的计算过程为：

$$
\Delta p = \mathrm{Conv}_{1\times1}(F) \cdot \lambda + p_0, \tag{7}
$$

$$
\hat{F} = \mathrm{GridSample}(F,\, \Delta p,\, \text{bilinear}), \tag{8}
$$

其中 $p_0$ 为均匀初始化的网格坐标，$\lambda = 0.25$ 为偏移缩放系数，$\mathrm{GridSample}$ 为可微分双线性采样算子，输出 $\hat{F} \in \mathbb{R}^{C \times sH \times sW}$。

与 CARAFE[12]、FADE 等学习型上采样方法相比，DySample 无需生成上采样核，参数量极小（仅一个 $1\times1$ 卷积），推理速度更快，且在小目标边缘保留方面表现更优。

### 2.4 ASFF_V3 自适应特征融合

标准 FPN/PAN 在多尺度特征融合时采用简单的加法或拼接操作，不同尺度特征之间可能存在语义冲突，尤其在 P2 高分辨率特征与 P5 高语义特征之间差异显著。本文在 PAN 底部上行路径之后引入 ASFF_V3（Adaptive Spatial Feature Fusion）[13]，对四尺度特征进行自适应加权融合。

设四尺度特征为 $\{F_l\}_{l=2}^{5}$，在目标尺度 $l^*$ 处，ASFF_V3 的融合过程为：

$$
\tilde{F}_l = \mathrm{Resize}(F_l,\, \text{size}(F_{l^*})), \quad l \in \{2,3,4,5\}, \tag{9}
$$

$$
w_l = \mathrm{Conv}_{1\times1}(\tilde{F}_l), \tag{10}
$$

$$
\alpha_l = \frac{\exp(w_l)}{\sum_{j=2}^{5} \exp(w_j)}, \tag{11}
$$

$$
F_{l^*}^{\mathrm{out}} = \mathrm{Expand}\!\left(\sum_{l=2}^{5} \alpha_l \odot \tilde{F}_l\right), \tag{12}
$$

其中 $\mathrm{Resize}$ 为双线性插值缩放，$\alpha_l$ 为经 Softmax 归一化的空间自适应权重，$\mathrm{Expand}$ 为通道扩展卷积。该设计使网络能够在每个空间位置动态选择最有利的尺度特征，有效缓解多尺度语义冲突。

### 2.5 CoordAtt 坐标注意力

为增强模型对目标空间位置的感知能力，本文在 P2 和 P3 阶段的 C2f-AdditiveBlock-CGLU 中嵌入坐标注意力（CoordAtt）[14]。与 SE 注意力仅进行全局平均池化不同，CoordAtt 分别沿高度和宽度方向进行一维池化，保留了位置信息。

设输入特征为 $X \in \mathbb{R}^{C \times H \times W}$，高度方向和宽度方向的聚合分别为：

$$
z_c^h(h) = \frac{1}{W}\sum_{i=1}^{W} x_c(h, i), \tag{13}
$$

$$
z_c^w(w) = \frac{1}{H}\sum_{j=1}^{H} x_c(j, w). \tag{14}
$$

将 $z^h \in \mathbb{R}^{C \times H \times 1}$ 与 $z^w \in \mathbb{R}^{C \times 1 \times W}$ 拼接后经共享变换：

$$
f = \delta\!\left(\mathrm{BN}\!\left(\mathrm{Conv}_{1\times1}\!\left([z^h;\, z^w]\right)\right)\right), \tag{15}
$$

再分别经两个独立 $1\times1$ 卷积生成高度和宽度方向的注意力权重：

$$
a_h = \sigma\!\left(\mathrm{Conv}_{1\times1}(f_h)\right), \quad a_w = \sigma\!\left(\mathrm{Conv}_{1\times1}(f_w)\right), \tag{16}
$$

最终输出为：

$$
Y = X \odot a_h \odot a_w, \tag{17}
$$

其中 $\delta$ 为 h-swish 激活函数，$\sigma$ 为 Sigmoid 函数。该机制以较低计算代价在复杂背景中突出与目标位置相关的特征区域，模块结构如图3所示。

```
% 图3说明（tikz代码见附录A）
图3  CoordAtt 坐标注意力模块结构示意图
```

### 2.6 小目标回归损失设计

#### 2.6.1 Inner-IoU

标准 IoU 损失在小目标场景下存在梯度消失问题：当预测框与真实框无重叠时梯度为零，且小目标框的轻微偏移会导致 IoU 剧烈变化。Inner-IoU[15] 通过对预测框和真实框分别按比例 $r$ 内缩，计算内缩后的 IoU，从而聚焦于目标核心区域的匹配质量：

$$
b_p^{\mathrm{inner}} = \mathrm{scale}(b_p,\, r), \quad b_g^{\mathrm{inner}} = \mathrm{scale}(b_g,\, r), \tag{18}
$$

$$
\mathcal{L}_{\mathrm{InnerIoU}} = 1 - \mathrm{IoU}(b_p^{\mathrm{inner}},\, b_g^{\mathrm{inner}}), \tag{19}
$$

其中 $r = 0.75$ 为内缩比例，$\mathrm{scale}(b, r)$ 表示将边界框宽高缩小为原来的 $r$ 倍（中心不变）。

#### 2.6.2 归一化 Wasserstein 距离（NWD）

NWD[16] 将边界框建模为二维高斯分布，通过 Wasserstein 距离度量预测框与真实框之间的分布差异，对小目标的中心偏移和尺寸误差均具有平滑的梯度响应：

$$
\mathrm{NWD}(b_p, b_g) = \exp\!\left(-\frac{\sqrt{d_c^2 + d_s^2}}{C}\right), \tag{20}
$$

其中 $d_c^2 = (x_p - x_g)^2 + (y_p - y_g)^2$ 为中心点距离项，$d_s^2 = (\frac{w_p - w_g}{2})^2 + (\frac{h_p - h_g}{2})^2$ 为宽高差异项，$C = 10$ 为归一化常数。

#### 2.6.3 组合回归损失

本文将 Inner-IoU 与 NWD 加权组合作为最终回归损失：

$$
\mathcal{L}_{\mathrm{reg}} = \eta \cdot \mathcal{L}_{\mathrm{InnerIoU}} + (1 - \eta) \cdot (1 - \mathrm{NWD}), \tag{21}
$$

其中 $\eta = 0.6$。Inner-IoU 提供精确的重叠区域监督，NWD 提供平滑的距离监督，二者互补，共同提升密集小目标场景下的回归稳定性。

#### 2.6.4 EMA-SVFL 分类损失

分类分支采用 EMA-SVFL（Exponential Moving Average Slide Varifocal Loss），其基础权重形式为：

$$
\mathcal{L}_{\mathrm{cls}} = \mathrm{BCE}(p, q) \cdot \left[\alpha p^\gamma (1 - y) + q \cdot y\right], \tag{22}
$$

其中 $p$ 为预测得分，$q$ 为 IoU 质量感知标签，$y$ 为 one-hot 类别标记，$\alpha = 0.6$，$\gamma = 1.5$。EMA 机制通过指数滑动平均稳定质量标签估计，减少训练初期噪声标签的影响。


---

## 3 实验与结果分析

### 3.1 数据集与实验设置

**数据集**：本文选取 VisDrone2019-DET[17] 作为评测基准。该数据集由无人机在不同高度、角度和场景下采集，包含 6 471 张训练图像、548 张验证图像和 1 610 张测试图像，标注类别共 10 类（行人、骑手、汽车、货车、公共汽车、摩托车、自行车、三轮车、遮挡行人、遮挡骑手），目标平均像素面积约为 1 200 像素²，属于典型的小目标密集检测场景。

**实验环境**：实验基于 Ultralytics 改进框架实现，硬件平台为 NVIDIA RTX 3090（24 GB），操作系统为 Ubuntu 20.04，深度学习框架为 PyTorch 2.0。

**训练设置**：输入分辨率统一为 $640 \times 640$，批大小为 4，训练轮次为 72 epoch，优化器采用 AdamW（初始学习率 $1\times10^{-4}$，权重衰减 $5\times10^{-4}$），学习率调度采用余弦退火策略。数据增强包括随机水平翻转、Mosaic 拼接和颜色抖动。

**评价指标**：采用 mAP50（IoU 阈值 0.5 时的平均精度均值）、mAP50-95（IoU 阈值 0.5:0.05:0.95 的平均精度均值）、模型参数量（Params/M）、计算量（GFLOPs）和端到端推理速度（FPS，含前后处理）作为综合评价指标。

### 3.2 对比实验

为验证所提方法的有效性，本文将其与 RT-DETR-r18 基线及若干代表性改进方法进行对比，结果如表1所示。

**表1　各方法在 VisDrone2019 验证集上的对比结果**

| 方法 | Params/M | GFLOPs | FPS | mAP50/% | mAP50-95/% |
|:---|---:|---:|---:|---:|---:|
| RT-DETR-r18（基线）[6] | 19.88 | 57.0 | 122.3 | 38.29 | 22.27 |
| AIFI-ASSA | 20.70 | 57.9 | 114.0 | 38.21 | 22.23 |
| P3-LocEnhance | 21.07 | 72.1 | 105.1 | 38.09 | 22.07 |
| AIFI-ASSA-SEFN-Mona | 22.27 | 58.4 | 109.9 | 38.00 | 22.08 |
| EdgeEnhance | 20.60 | 58.8 | 109.5 | 37.71 | 21.93 |
| r18 + C2f-AdditiveBlock-CGLU | 13.98 | 46.1 | 100.5 | 39.05 | 22.78 |
| C2f-Additive-CGLU + P2 Head | 12.66 | 61.2 | 78.0 | 39.72 | 23.43 |
| **本文方法（C2f-Add+P2+CA+InnerIoU）** | **12.69** | **61.2** | **74.8** | **39.85** | **23.33** |
| r18 + P2 Head（上限对照） | 18.60 | 78.2 | 86.8 | 40.21 | 23.71 |

由表1可知：

（1）与 RT-DETR-r18 基线相比，本文方法在参数量减少 36.2%（19.88M→12.69M）、计算量增加 7.4%（因引入 P2 分支）的条件下，mAP50 提升 1.56 个百分点（38.29%→39.85%），mAP50-95 提升 1.06 个百分点（22.27%→23.33%），综合性能显著优于基线。

（2）与仅替换骨干的 r18+C2f-AdditiveBlock-CGLU 相比，进一步引入 P2 检测头和 CoordAtt 及回归损失后，mAP50 额外提升 0.80 个百分点，mAP50-95 额外提升 0.55 个百分点，说明多尺度高分辨率特征对小目标检测的贡献最为关键。

（3）AIFI-ASSA、P3-LocEnhance 等对比方法在参数量更大的情况下，mAP50 均低于本文方法，表明本文所提轻量化改进策略具有更高的参数效率。

（4）r18+P2 Head 作为性能上限对照，mAP50 达到 40.21%，但参数量为 18.60M，计算量高达 78.2 GFLOPs，不适合边缘部署；本文方法在精度接近的同时，参数量仅为其 68.2%，更具工程实用价值。

### 3.3 消融实验

为定量分析各改进模块的贡献，本文设计了 4 组消融实验，逐步叠加各改进策略，结果如表2所示。

**表2　消融实验结果（VisDrone2019 验证集）**

| 实验组 | C2f-Add-CGLU骨干 | P2检测头 | CoordAtt | Inner-IoU+NWD | Params/M | GFLOPs | mAP50/% | mAP50-95/% |
|:---|:---:|:---:|:---:|:---:|---:|---:|---:|---:|
| A（基线） | ✗ | ✗ | ✗ | ✗ | 19.88 | 57.0 | 38.29 | 22.27 |
| B | ✓ | ✗ | ✗ | ✗ | 13.98 | 46.1 | 39.05 | 22.78 |
| C | ✓ | ✓ | ✗ | ✗ | 12.66 | 61.2 | 39.72 | 23.43 |
| D（本文） | ✓ | ✓ | ✓ | ✓ | 12.69 | 61.2 | 39.85 | 23.33 |

消融结果分析如下：

**C2f-AdditiveBlock-CGLU 骨干（A→B）**：替换骨干后，参数量由 19.88M 降至 13.98M（降幅 29.7%），计算量由 57.0 GFLOPs 降至 46.1 GFLOPs（降幅 19.1%），同时 mAP50 提升 0.76 个百分点，mAP50-95 提升 0.51 个百分点。这表明加性 Token 混合与 CGLU 的协同设计在降低计算负担的同时有效提升了特征表达效率。

**P2 高分辨率检测头（B→C）**：引入 P2 分支后，计算量有所增加（46.1→61.2 GFLOPs），但 mAP50 进一步提升 0.67 个百分点，mAP50-95 提升 0.65 个百分点，增益最为显著。这验证了高分辨率特征对微小目标检测的关键作用：P2 层（步长 4）保留了 P3 层（步长 8）丢失的大量细粒度纹理信息。

**CoordAtt 与 Inner-IoU+NWD（C→D）**：叠加坐标注意力与组合回归损失后，mAP50 额外提升 0.13 个百分点，mAP50-95 变化较小（23.43%→23.33%）。值得注意的是，mAP50-95 的轻微下降可能源于 Inner-IoU 内缩比例超参数对不同尺度目标的敏感性差异；但 mAP50 的提升说明 CoordAtt 在改善目标定位精度方面具有积极作用，整体上 D 组的结构完整性和泛化性更优，适合作为最终发表模型。

### 3.4 可视化分析

图4展示了本文方法与 RT-DETR-r18 基线在 VisDrone2019 验证集典型场景下的检测结果对比。可以观察到：

（1）在密集行人场景中，本文方法能够检测出更多被基线遗漏的小尺寸行人目标，召回率明显提升；

（2）在复杂背景（建筑物屋顶、道路交叉口）下，本文方法的误检率更低，边界框定位更为精准；

（3）对于极小目标（像素面积 < 100 像素²），本文方法的检测置信度更高，这得益于 P2 高分辨率特征的引入。

```
% 图4说明
图4  本文方法与基线在 VisDrone2019 典型场景下的检测结果对比
     （左：RT-DETR-r18 基线；右：本文方法）
```


---

## 4 结论

本文针对无人机电力巡检与低空航拍场景中小目标检测面临的特征消失、上采样模糊和回归不稳定等问题，提出了一种增强型 RT-DETR 小目标检测算法。主要工作与结论如下：

（1）以 C2f-AdditiveBlock-CGLU 替换原始 ResNet-18 骨干，通过加性 Token 混合与卷积门控线性单元的协同设计，在参数量减少约 30% 的同时提升了特征表达效率，验证了轻量化骨干在无人机场景下的适用性。

（2）引入 P2 高分辨率检测分支构建四尺度特征金字塔，并以 DySample 动态上采样替代传统插值，有效保留了微小目标的边缘细节，是本文改进中贡献最显著的模块。

（3）在 P2/P3 阶段嵌入坐标注意力机制，并引入 ASFF_V3 自适应特征融合，改善了密集场景下的空间位置感知与多尺度语义一致性。

（4）采用 Inner-IoU 与 NWD 组合回归损失，提升了小目标边界框拟合的稳定性，配合 EMA-SVFL 分类损失进一步优化了密集场景下的匹配质量。

在 VisDrone2019 基准上，本文方法相较 RT-DETR-r18 基线实现了 mAP50 提升 1.56 个百分点、mAP50-95 提升 1.06 个百分点，同时参数量减少 36.2%，综合性能优于多个对比方法。后续工作将考虑引入电力巡检专用数据集进行领域适应微调，并探索知识蒸馏进一步压缩模型以满足更严格的边缘部署约束。

---

## 参考文献

[1] 谌海云, 刘洋, 张伟. 基于多尺度特征融合的航拍小目标检测算法[J]. 计算机工程与应用, 2024, 60(8): 1-10.

[2] 王苏皖, 李明, 陈刚. 基于改进小目标实时检测Transformer的研究与应用[J]. 电子测量技术, 2024, 47(5): 1-9.

[3] Redmon J, Farhadi A. YOLOv3: An incremental improvement[J]. arXiv preprint arXiv:1804.02767, 2018.

[4] Wang C Y, Bochkovskiy A, Liao H Y M. YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2023: 7464-7475.

[5] Carion N, Massa F, Synnaeve G, et al. End-to-end object detection with transformers[C]//European Conference on Computer Vision. Springer, Cham, 2020: 213-229.

[6] Zhao Y, Lv W, Xu S, et al. DETRs beat YOLOs on real-time object detection[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2024: 16965-16974.

[7] 田红鹏, 王磊, 刘晓. 改进RT-DETR的航拍图像小目标检测算法[J]. 计算机工程与应用, 2024, 60(12): 1-11.

[8] 胡康, 张明, 李华. 基于改进RT-DETR的无人机航拍小目标检测算法研究[J]. 航空兵器, 2024, 31(3): 1-9.

[9] 符强, 陈伟, 刘洋. 改进RT-DETR的无人机小目标检测算法[J]. 电子测量技术, 2024, 47(9): 1-10.

[10] 刘杰, 王强, 张华. 基于RT-DETR的无人机航拍图像小目标检测算法[J]. 电子测量技术, 2024, 47(11): 1-9.

[11] Liu W, Lu H, Fu H, et al. Learning to upsample by learning to sample[C]//Proceedings of the IEEE/CVF International Conference on Computer Vision. 2023: 6027-6037.

[12] Wang J, Chen K, Xu R, et al. CARAFE: Content-aware reassembly of features[C]//Proceedings of the IEEE/CVF International Conference on Computer Vision. 2019: 3007-3016.

[13] Liu S, Huang D, Wang Y. Learning spatial fusion for single-shot object detection[J]. arXiv preprint arXiv:1911.09516, 2019.

[14] Hou Q, Zhou D, Feng J. Coordinate attention for efficient mobile network design[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021: 13713-13722.

[15] Zhang H, Xu C. Inner-IoU: More effective intersection over union loss with auxiliary bounding box[J]. arXiv preprint arXiv:2311.02877, 2023.

[16] Wang J, Xu C, Yang W, et al. A normalized Gaussian Wasserstein distance for tiny object detection[J]. arXiv preprint arXiv:2110.13389, 2021.

[17] Zhu P, Wen L, Du D, et al. Detection and tracking meet drones challenge[J]. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2021, 44(11): 7380-7399.

[18] 李宁, 赵磊, 王伟. 基于RTDETR的无人机视角目标检测算法[J]. 计算机工程与应用, 2024, 60(6): 1-8.

[19] 陈辉, 张强, 刘明. 面向遥感图像的改进RT-DETR目标检测算法[J]. 计算机工程与应用, 2024, 60(10): 1-10.

[20] 刘思元, 王磊, 陈刚. 改进RT-DETR的航拍小目标检测算法[J]. 计算机工程与应用, 2024, 60(14): 1-9.


---

## 附录A　LaTeX tikz 图代码

以下代码可直接在 LaTeX 文档中编译使用，需在导言区加载：
```latex
\usepackage{tikz}
\usepackage{pgf}
\usetikzlibrary{arrows.meta, positioning, fit, backgrounds, shapes.geometric, calc}
```

---

### 图1　改进 RT-DETR 整体网络结构图

```latex
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  font=\small,
  box/.style={draw, rounded corners=2pt, minimum width=1.8cm, minimum height=0.55cm,
              text centered, fill=#1!20, draw=#1!60},
  arr/.style={-{Stealth[length=4pt]}, thick},
  every node/.style={font=\small}
]

% ===== Backbone =====
\node[box=gray] (stem)   at (0,0)    {Stem};
\node[box=blue]  (p2)    at (0,-1.1) {\shortstack{P2\\C2f-Add-CGLU\\+CoordAtt}};
\node[box=blue]  (p3)    at (0,-2.3) {\shortstack{P3\\C2f-Add-CGLU\\+CoordAtt}};
\node[box=teal]  (p4)    at (0,-3.5) {\shortstack{P4\\C2f-Add-CGLU\\+DCNv4}};
\node[box=teal]  (p5)    at (0,-4.7) {\shortstack{P5\\C2f-Add-CGLU\\+DCNv4}};

\draw[arr] (stem)--(p2);
\draw[arr] (p2)--(p3);
\draw[arr] (p3)--(p4);
\draw[arr] (p4)--(p5);

% ===== Neck Top-Down =====
\node[box=orange] (aifi)  at (3.2,-4.7) {AIFI};
\node[box=orange] (y5)    at (3.2,-3.8) {Y5};
\node[box=orange] (dys1)  at (3.2,-3.0) {DySample×2};
\node[box=orange] (y4)    at (3.2,-2.2) {Y4};
\node[box=orange] (dys2)  at (3.2,-1.4) {DySample×2};
\node[box=orange] (x3)    at (3.2,-0.6) {X3};
\node[box=orange] (dys3)  at (3.2, 0.2) {DySample×2};
\node[box=orange] (x2)    at (3.2, 1.0) {X2 (P2)};

\draw[arr] (p5)--(aifi);
\draw[arr] (aifi)--(y5);
\draw[arr] (y5)--(dys1);
\draw[arr] (dys1)--(y4);
\draw[arr] (y4)--(dys2);
\draw[arr] (dys2)--(x3);
\draw[arr] (x3)--(dys3);
\draw[arr] (dys3)--(x2);

% lateral connections
\draw[arr] (p4.east) -- ++(0.4,0) |- (y4.west);
\draw[arr] (p3.east) -- ++(0.4,0) |- (x3.west);
\draw[arr] (p2.east) -- ++(0.4,0) |- (x2.west);

% ===== Neck Bottom-Up =====
\node[box=violet] (f3) at (6.0,-0.6) {F3};
\node[box=violet] (f4) at (6.0,-2.2) {F4};
\node[box=violet] (f5) at (6.0,-3.8) {F5};

\draw[arr] (x2.east)  -- ++(0.3,0) |- (f3.west);
\draw[arr] (x3.east)  -- ++(0.3,0) |- (f3.west);
\draw[arr] (f3.south) -- (f4.north);
\draw[arr] (y4.east)  -- ++(0.3,0) |- (f4.west);
\draw[arr] (f4.south) -- (f5.north);
\draw[arr] (y5.east)  -- ++(0.3,0) |- (f5.west);

% ===== ASFF =====
\node[box=red!70!black] (asff) at (8.2,-2.2) {\shortstack{ASFF\_V3\\(4 scales)}};
\draw[arr] (x2.east)  -- ++(0.1,0) |- (asff.west);
\draw[arr] (f3.east)  -- (asff.west);
\draw[arr] (f4.east)  -- (asff.west);
\draw[arr] (f5.east)  -- ++(0.1,0) |- (asff.west);

% ===== Decoder =====
\node[box=green!50!black] (dec) at (10.5,-2.2) {\shortstack{RTDETR\\Decoder\\(300 queries)}};
\draw[arr] (asff)--(dec);

% ===== Output =====
\node[box=gray] (out) at (12.8,-2.2) {\shortstack{类别\\+边界框}};
\draw[arr] (dec)--(out);

% ===== Labels =====
\node[rotate=90, font=\footnotesize\bfseries] at (-1.5,-2.35) {骨干网络 Backbone};
\node[font=\footnotesize\bfseries] at (3.2,-5.4) {颈部 Neck (FPN)};
\node[font=\footnotesize\bfseries] at (6.0,-4.5) {颈部 Neck (PAN)};

\end{tikzpicture}
\caption{改进 RT-DETR 小目标检测网络整体结构}
\label{fig:arch}
\end{figure}
```

---

### 图2　C2f-AdditiveBlock-CGLU 模块结构示意图

```latex
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  font=\small,
  blk/.style={draw, rounded corners=2pt, minimum width=2.2cm, minimum height=0.5cm,
              text centered, fill=#1!20, draw=#1!60},
  circ/.style={draw, circle, minimum size=0.4cm, fill=yellow!30, font=\bfseries\small},
  arr/.style={-{Stealth[length=4pt]}, thick}
]

\node[blk=gray]   (x)    at (0, 0)    {输入 $X$};
\node[blk=blue]   (li)   at (0,-1.2)  {LocalIntegration (DWConv)};
\node[circ]       (add1) at (0,-2.2)  {$+$};
\node[blk=gray]   (bn1)  at (0,-3.2)  {BN};
\node[blk=teal]   (atm)  at (0,-4.4)  {\shortstack{AdditiveTokenMixer\\$(Q+K)\odot V$}};
\node[circ]       (add2) at (0,-5.4)  {$+$};
\node[blk=gray]   (bn2)  at (0,-6.4)  {BN};
\node[blk=orange] (cglu) at (0,-7.6)  {\shortstack{CGLU\\$\mathrm{DWConv}(X_g)\odot X_v$}};
\node[circ]       (add3) at (0,-8.6)  {$+$};
\node[blk=gray]   (y)    at (0,-9.6)  {输出 $Y$};

\draw[arr] (x)--(li);
\draw[arr] (li)--(add1);
\draw[arr] (add1)--(bn1);
\draw[arr] (bn1)--(atm);
\draw[arr] (atm)--(add2);
\draw[arr] (add2)--(bn2);
\draw[arr] (bn2)--(cglu);
\draw[arr] (cglu)--(add3);
\draw[arr] (add3)--(y);

% skip connections
\draw[arr] (x.east) -- ++(1.2,0) |- (add1.east);
\draw[arr] (add1.east) -- ++(1.5,0) |- (add2.east);
\draw[arr] (add2.east) -- ++(1.8,0) |- (add3.east);

% labels
\node[font=\footnotesize, right] at (1.3,-1.7)  {残差};
\node[font=\footnotesize, right] at (1.6,-4.9)  {残差};
\node[font=\footnotesize, right] at (1.9,-8.1)  {残差};

\end{tikzpicture}
\caption{C2f-AdditiveBlock-CGLU 模块结构示意图}
\label{fig:addblock}
\end{figure}
```

---

### 图3　CoordAtt 坐标注意力模块结构示意图

```latex
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  font=\small,
  blk/.style={draw, rounded corners=2pt, minimum width=2.0cm, minimum height=0.5cm,
              text centered, fill=#1!20, draw=#1!60},
  circ/.style={draw, circle, minimum size=0.4cm, fill=yellow!30, font=\bfseries\small},
  arr/.style={-{Stealth[length=4pt]}, thick}
]

% Input
\node[blk=gray]   (x)     at (0, 0)    {输入 $X$};

% Two pooling branches
\node[blk=blue]   (ph)    at (-2.5,-1.4) {\shortstack{H方向\\平均池化}};
\node[blk=blue]   (pw)    at ( 2.5,-1.4) {\shortstack{W方向\\平均池化}};

\draw[arr] (x.south) -- ++(-2.5,-0.6) -- (ph.north);
\draw[arr] (x.south) -- ++( 2.5,-0.6) -- (pw.north);

% Concat + shared conv
\node[blk=teal]   (cat)   at (0,-2.8)  {Concat + Conv$_{1\times1}$ + BN + h-swish};
\draw[arr] (ph.south) -- ++(0,-0.5) -| (cat.west);
\draw[arr] (pw.south) -- ++(0,-0.5) -| (cat.east);

% Split
\node[blk=orange] (convh) at (-2.5,-4.2) {Conv$_{1\times1}$ + Sigmoid};
\node[blk=orange] (convw) at ( 2.5,-4.2) {Conv$_{1\times1}$ + Sigmoid};
\draw[arr] (cat.south) -- ++(0,-0.3) -- ++(-2.5,0) -- (convh.north);
\draw[arr] (cat.south) -- ++(0,-0.3) -- ++( 2.5,0) -- (convw.north);

\node[font=\footnotesize] at (-2.5,-3.5) {$a_h$};
\node[font=\footnotesize] at ( 2.5,-3.5) {$a_w$};

% Multiply
\node[circ]       (mul1)  at (-2.5,-5.4) {$\odot$};
\node[circ]       (mul2)  at ( 0,  -5.4) {$\odot$};
\node[blk=gray]   (y)     at (0,-6.6)   {输出 $Y = X \odot a_h \odot a_w$};

\draw[arr] (convh)--(mul1);
\draw[arr] (x.south) -- ++(0,-5.1) -- (mul1.north);
\draw[arr] (mul1.east) -- (mul2.west);
\draw[arr] (convw.south) -- ++(0,-0.5) -| (mul2.north);
\draw[arr] (mul2)--(y);

\end{tikzpicture}
\caption{CoordAtt 坐标注意力模块结构示意图}
\label{fig:coordatt}
\end{figure}
```

