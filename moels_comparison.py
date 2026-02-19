import matplotlib.pyplot as plt
import numpy as np

# 实验数据 (Params, mAP50)
# 格式: (Params(M), mAP50(%), 'Label', Color)
models = [
    (19.88, 38.29, 'RT-DETR-r18 (Baseline)', 'gray'),
    (13.98, 39.05, 'Ours-L (C2f-Add)', 'blue'),
    (13.34, 38.87, 'Ours-S (C2f-AP)', 'green'),
    (18.60, 40.21, 'r18 + P2 (Upper Bound)', 'orange'),
    (12.66, 39.72, 'Ours-Final (C2f-Add + P2)', 'red'),  # 你的王牌
    (20.70, 38.21, 'AIFI-ASSA', 'purple'),
    (21.07, 38.09, 'P3-LocEnhance', 'purple'),
]

# 提取数据
params = [m[0] for m in models]
maps = [m[1] for m in models]
labels = [m[2] for m in models]
colors = [m[3] for m in models]

# 创建画布
plt.figure(figsize=(10, 7), dpi=150)
plt.style.use('seaborn-v0_8-whitegrid') # 使用科研风格网格

# 绘制散点
plt.scatter(params, maps, c=colors, s=150, alpha=0.8, edgecolors='k', zorder=10)

# 特殊标注 Ours-Final
final_idx = 4
plt.scatter(params[final_idx], maps[final_idx], c='red', s=300, marker='*', edgecolors='k', zorder=11, label='Ours-Final')

# 添加标签
for i, label in enumerate(labels):
    offset_y = 0.15
    if i == 4: offset_y = -0.3 # 让Ours-Final标签往下一点，避开点
    plt.text(params[i], maps[i] + offset_y, label, fontsize=10, ha='center', fontweight='bold' if 'Ours' in label else 'normal')

# 装饰图表
plt.title('Trade-off between Parameters and Accuracy (VisDrone)', fontsize=14, fontweight='bold')
plt.xlabel('Parameters (M)', fontsize=12)
plt.ylabel('mAP50 (%)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)

# 绘制帕累托前沿 (可选虚线连接最优模型)
# 连接 Ours-S -> Ours-L -> Ours-Final -> r18+P2
pareto_x = [13.34, 13.98, 12.66, 18.60]
pareto_y = [38.87, 39.05, 39.72, 40.21]
# 注意：这里为了画线顺畅，按参数量排序连接可能更好，或者只连接 Ours 系列
plt.plot([12.66, 18.60], [39.72, 40.21], 'r--', alpha=0.5, label='Pareto Frontier')

plt.legend(loc='lower right')
plt.tight_layout()

# 保存
plt.savefig('efficiency_tradeoff.png')
plt.show()