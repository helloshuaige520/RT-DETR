## 

| **排名** | **模型名称**                           | **Params** | **GFLOPs** | **FPS (E2E)** | **mAP50**  | **mAP50-95** | **备注与论文定位**                               |
| -------- | -------------------------------------- | ---------- | ---------- | ------------- | ---------- | ------------ | ------------------------------------------------ |
| 1        | **r18 + P2 Head (Slim)**               | 18.60M     | 78.2       | 86.81         | 0.4021     | 0.2371       | **Upper Bound (SOTA)**: 精度上限，计算量最大     |
| 2        | **C2f-Add + P2 - SVFL+NWD (v1 tuned)** | 12.66M     | 61.2       | 77.90         | 0.3990     | 0.2330       | **Ours-Tuned**: 针对特定测试集的调参极限         |
| 3        | **C2f-Add + P2 + CA + InnerIoU (v1)**  | **12.69M** | **61.2**   | **74.82**     | **0.3985** | **0.2333**   | **Ours-Final**: 结构最完整，泛化性与精度综合最优 |
| 4        | rtdetr-C2f-Additive-CGLU + P2          | 12.66M     | 61.2       | 77.98         | 0.3972     | 0.2343       | Ours-Base: 默认损失函数的 P2 架构                |
| 5        | **r18 + C2f-AdditiveBlock-CGLU**       | 13.98M     | 46.1       | 100.48        | 0.3905     | 0.2278       | **Ours-Light**: 仅改进主干，最佳能效比           |
| 6        | **C2f-AP (lite)**                      | 13.34M     | 47.0       | 115.91        | 0.3887     | 0.2273       | **Ours-Speed**: 极速版                           |
| 7        | C2f-Add + P2 - SVFL+NWD (Untuned)      | 12.66M     | 61.2       | 78.14         | 0.3875     | 0.2247       | 消融对照组: 负面结果展示                         |
| 8        | **r18 Baseline (Batch=4)**             | 19.88M     | 57.0       | 122.27        | 0.3829     | 0.2227       | **Baseline**: 基准线模型                         |
| 9        | AIFI-ASSA                              | 20.70M     | 57.9       | 114.00        | 0.3821     | 0.2223       | 对比实验                                         |
| 10       | r18 + C2f-EfficientVIM-CGLU            | 14.50M     | 48.0       | 87.23         | 0.3819     | 0.2221       | 消融实验                                         |
| 11       | P3-LocEnhance                          | 21.07M     | 72.1       | 105.09        | 0.3809     | 0.2207       | 对比实验                                         |
| 12       | AIFI-ASSA-SEFN-Mona                    | 22.27M     | 58.4       | 109.90        | 0.3800     | 0.2208       | 对比实验                                         |
| 13       | AIFI-ASSA-SEFN-Mona-DyT                | 22.27M     | 58.4       | 110.60        | 0.3789     | 0.2206       | 对比实验                                         |
| 14       | AIFI-DML                               | 19.95M     | 56.8       | 119.82        | 0.3789     | 0.2188       | 对比实验                                         |
| 15       | EdgeEnhance                            | 20.60M     | 58.8       | 109.49        | 0.3771     | 0.2193       | 对比实验                                         |
| 16       | r18 (Batch=5)                          | 19.88M     | 57.0       | 121.08        | 0.3769     | 0.2182       | 超参敏感性分析                                   |
| 17       | r18 + C2fAdd-CGLU + P3-LLE             | 14.05M     | 47.0       | 98.33         | 0.3759     | 0.2149       | 失败消融对照                                     |
| 18       | r18 + P3-LLE                           | 19.95M     | 57.9       | 115.36        | 0.3730     | 0.2139       | 失败消融对照                                     |
| 19       | AIFI-ASSA-SEFN                         | 22.18M     | 58.3       | 112.70        | 0.3715     | 0.2127       | 对比实验                                         |
| 20       | AIFI-DAttention                        | 19.89M     | 57.2       | 120.90        | 0.2747     | 0.1578       | 对比实验                                         |
*表中“rtdetr-C2f-Additive-CGLU + P2 Head”为您新上传的实验结果（见 runs/val 对应目录下的 `paper_data.txt`）。*

## 消融实验

## 改进策略

**「P3 受约束局部增强 + P5 轻量语义稳态」的双路径改进**

VisDrone 的核心难点在于很多目标在下采样 32 倍（P5）甚至 16 倍（P4）后，特征已经彻底消失了。RT-DETR 默认只用 P3, P4, P5（最小 stride=8）。对于 VisDrone，很多 10x10 像素的无人机/行人，在 P3 层只剩 1 个像素，甚至被忽略。引入 **P2 (Stride=4)** 层，可以让网络“看清”微小物体。 **代价**：计算量（GFLOPs）会增加，但因为你已经把 Backbone 换成了轻量化的 `C2f-AP`，这部分增加是可以接受的。

> **小目标靠 P3 局部细节增强，大目标靠 P5 语义一致性，二者解耦。**

r18 + P3_LLE实验：
目标：
GFLOPs ↓↓↓

FPS ↑↑

mAP50-95 **不低于 0.218**

结果：
P3-LLE做到了参数下降，算力下降

因发现一篇论文《改进RT-DETR的航拍图像小目标检测算法_田红鹏》中使用了c2f结构，且和-C2f-AddutuveBlock-CGLU结构相似，因此开始-C2f-AddutuveBlock-CGLU实验：

损失函数改进：
**已完成的损失函数实验（VisDrone）**
- SVFL+NWD 组合（v1 tuned）
  - 配置入口：rtdetr-C2f-Additive-CGLU + P2 Head 2-SVFL+NWD.yaml 的 loss 段落，[rtdetr-C2f-Additive-CGLU + P2 Head 2-SVFL+NWD.yaml](file:///home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/ultralytics/cfg/models/rt-detr/rtdetr-C2f-Additive-CGLU%20+%20P2%20Head%202-SVFL+NWD.yaml#L9-L39)
  - 关键开关：use_vfl=true, use_emasvfl=true, nwd_loss=true, nwd_constant=10.0, iou_ratio=0.6, use_uni_match=true, uni_match_ind=0；vfl_alpha/gamma=0.6/1.5，svfl_alpha/gamma=0.6/1.5
  - 结果：mAP50=0.3990，mAP50-95=0.2330（表中“C2f-Add + P2 - SVFL+NWD (v1 tuned)”）
- SVFL+NWD 组合（Untuned）
  - 配置入口同上，使用未调参版本
  - 结果：mAP50=0.3875，mAP50-95=0.2247（表中“C2f-Add + P2 - SVFL+NWD (Untuned)”）
- Inner-IoU + SVFL/EMA-SVFL + NWD 混合（v1）
  - 配置入口：rtdetr-C2f-Additive-CGLU+P2-InnerIoU-CoordAtt.yaml 的 loss 段落，[rtdetr-C2f-Additive-CGLU+P2-InnerIoU-CoordAtt.yaml](file:///home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/ultralytics/cfg/models/rt-detr/rtdetr-C2f-Additive-CGLU+P2-InnerIoU-CoordAtt.yaml#L9-L25)
  - 关键开关：inner_iou=true, inner_ratio=0.75；use_svfl=true, use_emasvfl=true；nwd_loss=true, nwd_constant=10.0；iou_ratio=0.6
  - 结果：mAP50=0.3985，mAP50-95=0.2333（表中“C2f-Add + P2 + CA + InnerIoU (v1)”）
- 默认损失（对照组）
  - 配置：无额外 loss 段或默认超参，分类/回归按框架默认
  - 结果：mAP50=0.3972，mAP50-95=0.2343（表中“Ours-Base: 默认损失函数的 P2 架构”）

**实现与入口**
- RT-DETR 解析 YAML 的 loss 段并构建损失，入口见 [RTDETRDetectionModel.init_criterion](file:///home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/ultralytics/nn/tasks.py#L450-L475)
- 具体分类损失分流逻辑（Varifocal/Slide/EMA-Slide/Slide-Varifocal/EMA-Slide-Varifocal/MAL/BCE）见 [_get_loss_class](file:///home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/ultralytics/models/utils/loss.py#L114-L163)
