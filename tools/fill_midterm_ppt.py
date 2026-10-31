#!/usr/bin/env python3
import html
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PPT = ROOT / "中期答辩" / "RT-DETR_UAV_small_object_detection_8page_outline.pptx"
OUT = ROOT / "中期答辩" / "RT-DETR_UAV_small_object_detection_8page_outline_filled.pptx"

W, H = 12191695, 6858000


def emu(cm):
    return int(cm * 360000)


def esc(s):
    return html.escape(str(s), quote=True)


def color(hex_color):
    return hex_color.replace("#", "").upper()


def solid_fill(hex_color):
    return f'<a:solidFill><a:srgbClr val="{color(hex_color)}"/></a:solidFill>'


def line(hex_color="FFFFFF", width=0):
    if width <= 0:
        return "<a:ln><a:noFill/></a:ln>"
    return f'<a:ln w="{width}">{solid_fill(hex_color)}</a:ln>'


def text_runs(text, size=20, fill="1F2937", bold=False):
    lines = str(text).split("\n")
    ps = []
    b = ' b="1"' if bold else ""
    for line_text in lines:
        ps.append(
            f'<a:p><a:r><a:rPr lang="zh-CN" sz="{int(size*100)}"{b}>'
            f'<a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/>'
            f'{solid_fill(fill)}</a:rPr><a:t>{esc(line_text)}</a:t></a:r>'
            f'<a:endParaRPr lang="zh-CN" sz="{int(size*100)}"/></a:p>'
        )
    return "".join(ps)


def shape(sid, x, y, cx, cy, text="", font=20, fill=None, txt="1F2937",
          bold=False, radius=False, align="l", line_color="FFFFFF", line_w=0):
    fill_xml = solid_fill(fill) if fill else "<a:noFill/>"
    prst = "roundRect" if radius else "rect"
    body = text_runs(text, font, txt, bold)
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{sid}" name="TextBox {sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>{fill_xml}{line(line_color, line_w)}</p:spPr>
  <p:txBody><a:bodyPr wrap="square" anchor="mid"/><a:lstStyle/>{body}</p:txBody>
</p:sp>"""


def title(sid, text, page):
    return (
        shape(sid, emu(0.7), emu(0.35), emu(27.0), emu(0.85), text, 26, None, "0F172A", True)
        + shape(sid + 1, emu(0.7), emu(1.25), emu(3.2), emu(0.08), "", fill="2563EB")
        + shape(sid + 2, emu(30.9), emu(0.45), emu(2.0), emu(0.45), page, 12, "E0F2FE", "0369A1", True, True)
    )


def pic(sid, rid, x, y, cx, cy, name="Picture"):
    return f"""
<p:pic>
  <p:nvPicPr><p:cNvPr id="{sid}" name="{esc(name)}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
  <p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
  <p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
</p:pic>"""


def rect(sid, x, y, cx, cy, fill, ln="FFFFFF", lw=0):
    return shape(sid, x, y, cx, cy, "", 1, fill, "FFFFFF", False, False, "l", ln, lw)


def slide_xml(content):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:bg><p:bgPr>{solid_fill("F8FAFC")}<a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {content}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


def rels_xml(image_targets):
    base = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>',
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide1.xml"/>',
    ]
    for rid, target in image_targets:
        base.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{target}"/>')
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(base) + "</Relationships>"


def bars(start_id, data, x, y, w, h, maxv, color_hex="2563EB", label="mAP50"):
    out = []
    out.append(shape(start_id, x, y - emu(0.55), w, emu(0.35), label, 13, None, "334155", True))
    gap = emu(0.2)
    bw = (w - gap * (len(data) - 1)) // len(data)
    for i, (name, val, clr) in enumerate(data):
        bh = int(h * val / maxv)
        bx = x + i * (bw + gap)
        by = y + h - bh
        out.append(rect(start_id + 10 + i, bx, by, bw, bh, clr or color_hex))
        out.append(shape(start_id + 30 + i, bx, by - emu(0.35), bw, emu(0.3), f"{val:.3f}", 9, None, "0F172A", True))
        out.append(shape(start_id + 50 + i, bx - emu(0.05), y + h + emu(0.08), bw + emu(0.1), emu(0.5), name, 8.5, None, "475569"))
    out.append(rect(start_id + 90, x, y + h, w, emu(0.02), "94A3B8"))
    return "".join(out)


def metric_card(sid, x, y, title_text, value, note, fill):
    return (
        shape(sid, x, y, emu(5.0), emu(1.55), "", 1, fill, "FFFFFF", False, True)
        + shape(sid + 1, x + emu(0.25), y + emu(0.18), emu(4.5), emu(0.35), title_text, 10, None, "E0F2FE", True)
        + shape(sid + 2, x + emu(0.25), y + emu(0.5), emu(4.5), emu(0.55), value, 20, None, "FFFFFF", True)
        + shape(sid + 3, x + emu(0.25), y + emu(1.05), emu(4.5), emu(0.32), note, 8.5, None, "DBEAFE")
    )


def table(start_id, rows, x, y, widths, row_h=0.58):
    out = []
    colors = ["E2E8F0", "FFFFFF"]
    for r, row in enumerate(rows):
        yy = y + emu(row_h * r)
        bg = "DBEAFE" if r == 0 else colors[r % 2]
        xx = x
        for c, txt in enumerate(row):
            out.append(rect(start_id + r * 20 + c, xx, yy, emu(widths[c]), emu(row_h), bg, "CBD5E1", 7000))
            out.append(shape(start_id + 500 + r * 20 + c, xx + emu(0.06), yy + emu(0.03), emu(widths[c] - 0.12), emu(row_h - 0.06), txt, 8.6 if r else 9.2, None, "0F172A", r == 0))
            xx += emu(widths[c])
    return "".join(out)


def build_slides():
    img = {
        "sample": "dataset/images/train/000002.jpg",
        "overall": "my article/generated_figures/fig1_overall.png",
        "modules": "my article/generated_figures/fig2_modules.png",
        "loss": "my article/generated_figures/fig3_loss.png",
        "pr": "runs/train/exp-visdrone2019-rtdetr-C2f-Additive-CGLU + P2 Head/PR_curve.png",
        "f1": "runs/train/exp-visdrone2019-rtdetr-C2f-Additive-CGLU + P2 Head/F1_curve.png",
        "pred": "runs/train/exp-visdrone2019-rtdetr-C2f-Additive-CGLU + P2 Head/val_batch0_pred.jpg",
        "cm": "runs/train/exp-visdrone2019-rtdetr-C2f-Additive-CGLU + P2 Head/confusion_matrix_normalized.png",
    }
    media = {}
    for i, (k, rel) in enumerate(img.items(), 1):
        src = ROOT / rel
        ext = src.suffix.lower()
        media[k] = (src, f"filled_{i}{ext}")

    slides = {}
    rels = {}

    slides[1] = slide_xml(
        rect(11, emu(0), emu(0), emu(34), emu(10), "F8FAFC")
        + rect(12, emu(18.0), emu(0), emu(16.0), emu(10.0), "E0F2FE")
        + pic(10, "rId3", emu(18.8), emu(0.85), emu(12.6), emu(5.6), "UAV sample")
        + shape(13, emu(1.05), emu(1.1), emu(19.5), emu(1.45), "面向无人机航拍场景的\nRT-DETR 小目标检测算法改进研究", 28, None, "0F172A", True)
        + shape(14, emu(1.1), emu(3.2), emu(13.2), emu(0.55), "研究生中期考核答辩", 16, "2563EB", "FFFFFF", True, True)
        + shape(15, emu(1.1), emu(4.0), emu(15.7), emu(1.7), "研究对象：VisDrone 无人机航拍图像\n核心任务：小目标、密集遮挡、复杂背景下的实时检测\n技术路线：RT-DETR-r18 + 轻量特征增强 + P2-P5 多尺度融合 + 损失优化", 15, None, "334155")
        + shape(16, emu(1.1), emu(6.05), emu(4.0), emu(0.55), "UAV", 15, "DBEAFE", "1D4ED8", True, True)
        + shape(17, emu(5.4), emu(6.05), emu(4.0), emu(0.55), "RT-DETR", 15, "DCFCE7", "166534", True, True)
        + shape(18, emu(9.7), emu(6.05), emu(4.6), emu(0.55), "小目标检测", 15, "FEF3C7", "92400E", True, True)
        + shape(19, emu(30.9), emu(6.9), emu(2.0), emu(0.45), "01/08", 12, "E0F2FE", "0369A1", True, True)
    )
    rels[1] = [("rId3", media["sample"][1])]

    slides[2] = slide_xml(
        title(20, "一、研究背景与意义", "02/08")
        + pic(21, "rId3", emu(19.4), emu(1.45), emu(12.1), emu(4.6), "Dataset sample")
        + shape(22, emu(0.9), emu(1.75), emu(16.6), emu(1.0), "无人机平台在交通巡检、城市治理、应急搜救和低空安防中快速普及，航拍目标检测需要同时满足高精度与实时性。", 17, None, "334155")
        + shape(23, emu(0.95), emu(3.1), emu(5.0), emu(1.65), "小目标占比高\n目标尺寸小，深层特征响应弱，漏检风险高。", 14, "EFF6FF", "1E3A8A", True, True)
        + shape(24, emu(6.35), emu(3.1), emu(5.0), emu(1.65), "场景干扰强\n道路、建筑、树木与光照变化导致误检。", 14, "F0FDF4", "166534", True, True)
        + shape(25, emu(11.75), emu(3.1), emu(5.0), emu(1.65), "实时要求高\n端侧或巡检任务要求较高 FPS。", 14, "FFF7ED", "9A3412", True, True)
        + shape(26, emu(0.95), emu(5.35), emu(16.4), emu(1.0), "选用 RT-DETR 的原因：端到端检测、无需复杂 NMS、兼具 CNN 高效特征提取与 Transformer 全局建模能力，适合作为无人机小目标检测改进基线。", 15, None, "334155")
        + shape(27, emu(19.4), emu(6.25), emu(12.0), emu(0.45), "图：训练集中航拍视角样例，目标尺度小且分布密集", 10, None, "64748B")
    )
    rels[2] = [("rId3", media["sample"][1])]

    slides[3] = slide_xml(
        title(30, "二、研究现状与问题分析", "03/08")
        + shape(33, emu(0.9), emu(1.55), emu(15.2), emu(0.6), "RT-DETR 在航拍小目标中的主要不足", 18, None, "0F172A", True)
        + shape(34, emu(0.95), emu(2.35), emu(7.0), emu(1.25), "1. 小目标特征易丢失\nP3/P4/P5 多次下采样后，小目标仅剩少量像素响应。", 13.5, "FFFFFF", "334155", True, True, line_color="CBD5E1", line_w=9000)
        + shape(35, emu(8.3), emu(2.35), emu(7.0), emu(1.25), "2. 浅层细节利用不足\n原始结构未充分引入 P2 高分辨率特征。", 13.5, "FFFFFF", "334155", True, True, line_color="CBD5E1", line_w=9000)
        + shape(36, emu(0.95), emu(3.95), emu(7.0), emu(1.25), "3. 背景与遮挡复杂\n密集场景下边界、纹理与类别信息容易混淆。", 13.5, "FFFFFF", "334155", True, True, line_color="CBD5E1", line_w=9000)
        + shape(37, emu(8.3), emu(3.95), emu(7.0), emu(1.25), "4. 小框定位不稳定\n预测框轻微偏移就会造成 IoU 大幅下降。", 13.5, "FFFFFF", "334155", True, True, line_color="CBD5E1", line_w=9000)
        + shape(38, emu(17.0), emu(1.7), emu(13.7), emu(4.0), "研究切入点\n• 保留浅层细节：引入 P2/高分辨率特征\n• 强化跨尺度融合：P2-P5 联合建模\n• 增强局部结构：边缘、位置与语义协同\n• 优化定位损失：提升小框回归稳定性", 16, "EFF6FF", "1E3A8A", True, True)
        + shape(39, emu(1.0), emu(6.05), emu(29.6), emu(0.7), "问题归纳：需要同时解决“细节保持、跨尺度融合、先验引导、定位稳定”四类问题。", 17, "DBEAFE", "1E40AF", True, True)
    )
    rels[3] = []

    slides[4] = slide_xml(
        title(40, "三、研究内容与技术路线", "04/08")
        + pic(43, "rId3", emu(1.0), emu(1.55), emu(16.0), emu(4.5), "Overall framework")
        + shape(44, emu(18.0), emu(1.45), emu(12.8), emu(0.55), "改进框架：DSDC-SPAFM-SAIW", 17, None, "0F172A", True)
        + shape(45, emu(18.0), emu(2.15), emu(12.7), emu(3.0), "• Backbone：以 RT-DETR-r18 为基础，引入轻量 C2f/Additive/CGLU 类结构，降低参数量并增强局部表达。\n• Neck：扩展到 P2-P5 四尺度，补充小目标浅层细节。\n• SPAFM：利用浅层空间先验引导多尺度融合，提升密集目标可分性。\n• SAIW/Inner-Wasserstein：缓解小目标框 IoU 对偏移过敏的问题。", 13.5, None, "334155")
        + shape(46, emu(1.0), emu(6.2), emu(29.8), emu(0.45), "技术主线：轻量特征提取 → 高分辨率小目标特征 → 先验引导融合 → 尺度感知定位优化", 13.5, "0F172A", "FFFFFF", True, True)
    )
    rels[4] = [("rId3", media["overall"][1])]

    slides[5] = slide_xml(
        title(50, "四、改进模块设计", "05/08")
        + pic(53, "rId3", emu(1.0), emu(1.55), emu(14.3), emu(4.55), "Modules")
        + shape(54, emu(16.4), emu(1.55), emu(14.6), emu(0.55), "DSDC 细节语义双路径协同", 17, None, "0F172A", True)
        + shape(55, emu(16.4), emu(2.25), emu(6.9), emu(1.35), "细节分支\n关注纹理、边缘、位置等局部线索，减少小目标下采样后的信息损失。", 13, "EFF6FF", "1E40AF", True, True)
        + shape(56, emu(24.0), emu(2.25), emu(6.9), emu(1.35), "语义分支\n增强上下文表达，降低复杂背景下的误检。", 13, "F0FDF4", "166534", True, True)
        + shape(57, emu(16.4), emu(4.0), emu(14.5), emu(1.25), "门控融合与坐标注意力用于自适应分配细节/语义权重，使模型在小目标密集、遮挡和尺度变化场景下更稳定。", 14, None, "334155")
        + shape(58, emu(16.4), emu(5.65), emu(14.5), emu(0.75), "阶段性结论：主干轻量化后仍保持较高精度，Ours-Light 达到 mAP50 0.3905、FPS 100.48。", 14, "FEF3C7", "92400E", True, True)
    )
    rels[5] = [("rId3", media["modules"][1])]

    slides[6] = slide_xml(
        title(60, "五、P2-P5 多尺度融合与训练曲线", "06/08")
        + pic(63, "rId3", emu(0.85), emu(1.45), emu(14.6), emu(4.25), "Loss curves")
        + pic(64, "rId4", emu(16.3), emu(1.45), emu(6.7), emu(3.15), "PR curve")
        + pic(65, "rId5", emu(23.8), emu(1.45), emu(6.7), emu(3.15), "F1 curve")
        + shape(66, emu(0.95), emu(5.85), emu(14.4), emu(0.55), "训练趋势：损失整体下降，验证指标随训练推进趋于稳定。", 12.5, "E0F2FE", "075985", True, True)
        + shape(67, emu(16.3), emu(4.95), emu(14.2), emu(1.45), "P2 Head 的作用：引入 stride=4 高分辨率特征，增强小目标细节保持；与轻量主干组合后，计算量可控，并在 VisDrone 对比实验中取得更高 mAP。", 13.5, None, "334155")
    )
    rels[6] = [("rId3", media["loss"][1]), ("rId4", media["pr"][1]), ("rId5", media["f1"][1])]

    top_rows = [
        ["模型", "Params", "GFLOPs", "FPS", "mAP50", "mAP50-95"],
        ["r18 + P2 Head", "18.60M", "78.2", "86.81", "0.4021", "0.2371"],
        ["C2f-Add + P2 + CA + InnerIoU", "12.69M", "61.2", "74.82", "0.3985", "0.2333"],
        ["C2f-Add + P2", "12.66M", "61.2", "77.98", "0.3972", "0.2343"],
        ["r18 + C2f-Add-CGLU", "13.98M", "46.1", "100.48", "0.3905", "0.2278"],
        ["r18 Baseline", "19.88M", "57.0", "122.27", "0.3829", "0.2227"],
    ]
    bar_data = [
        ("Baseline", 0.3829, "94A3B8"),
        ("Ours-Light", 0.3905, "10B981"),
        ("P2 Base", 0.3972, "2563EB"),
        ("Final", 0.3985, "7C3AED"),
        ("SOTA", 0.4021, "F59E0B"),
    ]
    slides[7] = slide_xml(
        title(70, "六、阶段性实验结果", "07/08")
        + metric_card(73, emu(0.9), emu(1.35), "最佳精度", "mAP50 0.4021", "r18 + P2 Head", "1D4ED8")
        + metric_card(77, emu(6.2), emu(1.35), "综合模型", "mAP50 0.3985", "CA + InnerIoU", "7C3AED")
        + metric_card(81, emu(11.5), emu(1.35), "轻量模型", "100.48 FPS", "13.98M 参数", "059669")
        + table(90, top_rows, emu(0.9), emu(3.25), [6.2, 2.0, 2.0, 2.0, 2.0, 2.25], 0.52)
        + bars(300, bar_data, emu(18.1), emu(2.0), emu(12.2), emu(3.3), 0.41, label="mAP50 对比")
        + shape(390, emu(18.1), emu(5.95), emu(12.1), emu(0.55), "相对 Baseline：最高 mAP50 提升 +1.92 个百分点；轻量模型参数下降约 29.7%。", 12.2, "FEF3C7", "92400E", True, True)
    )
    rels[7] = []

    slides[8] = slide_xml(
        title(80, "七、可视化结果与后续计划", "08/08")
        + pic(83, "rId3", emu(0.8), emu(1.3), emu(10.1), emu(4.35), "Prediction")
        + pic(84, "rId4", emu(11.4), emu(1.3), emu(7.0), emu(4.35), "Confusion matrix")
        + shape(85, emu(19.2), emu(1.35), emu(11.6), emu(0.55), "中期后工作安排", 17, None, "0F172A", True)
        + shape(86, emu(19.2), emu(2.15), emu(11.6), emu(0.65), "1. 完成 Final 模型全量训练与测试集评估", 13.5, "EFF6FF", "1E40AF", True, True)
        + shape(87, emu(19.2), emu(3.0), emu(11.6), emu(0.65), "2. 补充 DSDC / P2 / SPAFM / SAIW 消融实验", 13.5, "F0FDF4", "166534", True, True)
        + shape(88, emu(19.2), emu(3.85), emu(11.6), emu(0.65), "3. 统计 Params、GFLOPs、FPS，分析精度-速度平衡", 13.5, "FFF7ED", "9A3412", True, True)
        + shape(89, emu(19.2), emu(4.7), emu(11.6), emu(0.65), "4. 整理论文图表、对比实验与答辩材料", 13.5, "F5F3FF", "6D28D9", True, True)
        + shape(90, emu(0.95), emu(5.9), emu(17.3), emu(0.45), "图：预测结果与归一化混淆矩阵，用于展示小目标检测效果和类别混淆情况。", 10.5, None, "64748B")
        + shape(91, emu(19.2), emu(5.75), emu(11.6), emu(0.65), "预期目标：形成一套面向无人机航拍场景的小目标实时检测改进方案。", 13, "0F172A", "FFFFFF", True, True)
    )
    rels[8] = [("rId3", media["pred"][1]), ("rId4", media["cm"][1])]

    return slides, rels, media


def main():
    slides, slide_rels, media = build_slides()
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        with zipfile.ZipFile(PPT) as z:
            z.extractall(t)

        media_dir = t / "ppt" / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        for src, name in media.values():
            if src.exists():
                shutil.copyfile(src, media_dir / name)
            else:
                raise FileNotFoundError(src)

        for i in range(1, 9):
            (t / "ppt" / "slides" / f"slide{i}.xml").write_text(slides[i], encoding="utf-8")
            (t / "ppt" / "slides" / "_rels" / f"slide{i}.xml.rels").write_text(
                rels_xml(slide_rels[i]), encoding="utf-8"
            )

        if OUT.exists():
            OUT.unlink()
        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zout:
            for path in sorted(t.rglob("*")):
                if path.is_file():
                    zout.write(path, path.relative_to(t).as_posix())
    print(OUT)


if __name__ == "__main__":
    main()
