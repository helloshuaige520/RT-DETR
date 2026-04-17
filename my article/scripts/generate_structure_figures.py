#!/usr/bin/env python3
from __future__ import annotations

import copy
import gzip
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
DOCX_IN = ROOT / "my article/RTDETR_中文核心论文_按模板重排_完善版.docx"
DOCX_OUT = ROOT / "my article/RTDETR_中文核心论文_结构图版.docx"
FIG_DIR = ROOT / "my article/generated_figures"
FONT_PATH = Path("/usr/share/consolefonts/Lat38-Fixed15.psf.gz")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {
    "w": W_NS,
    "r": R_NS,
    "wp": WP_NS,
    "a": A_NS,
    "pic": PIC_NS,
    "ct": CT_NS,
    "rel": REL_NS,
}

for prefix, uri in [("w", W_NS), ("r", R_NS), ("wp", WP_NS), ("a", A_NS), ("pic", PIC_NS)]:
    ET.register_namespace(prefix, uri)


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def get_text(el: ET.Element) -> str:
    return "".join(t.text or "" for t in el.findall(".//w:t", NS))


def strip_ws(text: str) -> str:
    return " ".join(text.split())


@dataclass
class Color:
    r: int
    g: int
    b: int

    def rgb(self) -> tuple[int, int, int]:
        return self.r, self.g, self.b


WHITE = Color(255, 255, 255)
BLACK = Color(34, 34, 34)
GREY = Color(110, 110, 110)
LIGHT_GREY = Color(225, 225, 225)
DASH_GREY = Color(150, 150, 150)
BLUE = Color(174, 212, 246)
BLUE2 = Color(224, 238, 252)
GREEN = Color(203, 232, 201)
GREEN2 = Color(234, 246, 233)
YELLOW = Color(251, 233, 170)
YELLOW2 = Color(255, 247, 221)
PINK = Color(245, 210, 228)
PINK2 = Color(252, 239, 246)
PEACH = Color(247, 211, 186)
PEACH2 = Color(252, 239, 228)
ORANGE = Color(245, 190, 117)
PURPLE = Color(210, 201, 245)
MINT = Color(190, 233, 220)
RED = Color(228, 94, 94)
PATH_RED = Color(227, 80, 80)
PATH_BLUE = Color(67, 132, 219)
PATH_GREEN = Color(72, 166, 117)
PATH_GOLD = Color(233, 180, 56)


class PSFFont:
    def __init__(self, path: Path) -> None:
        raw = gzip.open(path, "rb").read()
        if raw[:2] == b"\x36\x04":
            mode = raw[2]
            self.height = raw[3]
            self.width = 8
            self.num_glyph = 512 if mode & 0x01 else 256
            glyph_bytes = self.height
            offset = 4
        else:
            magic, version, headersize, flags, num_glyph, glyph_bytes, height, width = struct.unpack(
                "<IIIIIIII", raw[:32]
            )
            if magic != 0x864AB572:
                raise ValueError("Unsupported PSF font format")
            self.height = height
            self.width = width
            self.num_glyph = num_glyph
            offset = headersize
        self.glyphs: dict[int, list[list[int]]] = {}
        row_bytes = (self.width + 7) // 8
        for code in range(min(self.num_glyph, 256)):
            start = offset + code * glyph_bytes
            glyph = raw[start : start + glyph_bytes]
            rows: list[list[int]] = []
            for y in range(self.height):
                row = []
                line = glyph[y * row_bytes : (y + 1) * row_bytes]
                bits = int.from_bytes(line, "big")
                for x in range(self.width):
                    shift = row_bytes * 8 - 1 - x
                    row.append((bits >> shift) & 1)
                rows.append(row)
            self.glyphs[code] = rows

    def measure(self, text: str, scale: int = 1) -> tuple[int, int]:
        lines = text.split("\n")
        width = max((len(line) * (self.width + 1) - 1 for line in lines), default=0)
        height = len(lines) * self.height + max(0, len(lines) - 1) * 2
        return width * scale, height * scale


class Canvas:
    def __init__(self, width: int, height: int, bg: Color = WHITE) -> None:
        self.width = width
        self.height = height
        self.buf = bytearray(bg.rgb() * (width * height))

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.buf[i : i + 3] = bytes(color.rgb())

    def fill_rect(self, x: int, y: int, w: int, h: int, color: Color) -> None:
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        if x0 >= x1 or y0 >= y1:
            return
        line = bytes(color.rgb()) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.width + x0) * 3
            self.buf[i : i + len(line)] = line

    def rect(self, x: int, y: int, w: int, h: int, fill: Color | None = None, outline: Color | None = None, border: int = 2) -> None:
        if fill is not None:
            self.fill_rect(x, y, w, h, fill)
        if outline is not None and border > 0:
            self.fill_rect(x, y, w, border, outline)
            self.fill_rect(x, y + h - border, w, border, outline)
            self.fill_rect(x, y, border, h, outline)
            self.fill_rect(x + w - border, y, border, h, outline)

    def dashed_rect(self, x: int, y: int, w: int, h: int, color: Color, dash: int = 14, gap: int = 8, border: int = 2) -> None:
        for xx in range(x, x + w, dash + gap):
            self.fill_rect(xx, y, min(dash, x + w - xx), border, color)
            self.fill_rect(xx, y + h - border, min(dash, x + w - xx), border, color)
        for yy in range(y, y + h, dash + gap):
            self.fill_rect(x, yy, border, min(dash, y + h - yy), color)
            self.fill_rect(x + w - border, yy, border, min(dash, y + h - yy), color)

    def line(self, x1: int, y1: int, x2: int, y2: int, color: Color, width: int = 2) -> None:
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            self.fill_rect(x1 - width // 2, y1 - width // 2, width, width, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy

    def arrow(self, x1: int, y1: int, x2: int, y2: int, color: Color, width: int = 3, head: int = 14) -> None:
        self.line(x1, y1, x2, y2, color, width)
        angle = math.atan2(y2 - y1, x2 - x1)
        a1 = angle + math.pi * 0.82
        a2 = angle - math.pi * 0.82
        hx1 = int(x2 + head * math.cos(a1))
        hy1 = int(y2 + head * math.sin(a1))
        hx2 = int(x2 + head * math.cos(a2))
        hy2 = int(y2 + head * math.sin(a2))
        self.line(x2, y2, hx1, hy1, color, width)
        self.line(x2, y2, hx2, hy2, color, width)

    def poly_arrow(self, points: list[tuple[int, int]], color: Color, width: int = 3, head: int = 14) -> None:
        if len(points) < 2:
            return
        for (x1, y1), (x2, y2) in zip(points[:-2], points[1:-1]):
            self.line(x1, y1, x2, y2, color, width)
        (x1, y1), (x2, y2) = points[-2], points[-1]
        self.arrow(x1, y1, x2, y2, color, width, head)

    def circle(self, cx: int, cy: int, r: int, fill: Color | None = None, outline: Color | None = None) -> None:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = (x - cx) * (x - cx) + (y - cy) * (y - cy)
                if fill is not None and d <= r * r:
                    self.set_pixel(x, y, fill)
                if outline is not None and r * r - r <= d <= r * r + r:
                    self.set_pixel(x, y, outline)

    def text(self, x: int, y: int, text: str, font: PSFFont, color: Color = BLACK, scale: int = 1, align: str = "left") -> None:
        lines = text.split("\n")
        widths = [font.measure(line, scale)[0] for line in lines]
        total_h = font.measure(text, scale)[1]
        yy = y
        for idx, line in enumerate(lines):
            xx = x
            if align == "center":
                xx = x - widths[idx] // 2
            elif align == "right":
                xx = x - widths[idx]
            for ch in line:
                glyph = font.glyphs.get(ord(ch), font.glyphs.get(ord("?")))
                if glyph is None:
                    xx += (font.width + 1) * scale
                    continue
                for gy, row in enumerate(glyph):
                    for gx, bit in enumerate(row):
                        if bit:
                            self.fill_rect(xx + gx * scale, yy + gy * scale, scale, scale, color)
                xx += (font.width + 1) * scale
            yy += (font.height + 2) * scale

    def save_png(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            rows.append(0)
            start = y * stride
            rows.extend(self.buf[start : start + stride])

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        png = bytearray()
        png.extend(b"\x89PNG\r\n\x1a\n")
        png.extend(chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)))
        png.extend(chunk(b"IDAT", zlib.compress(bytes(rows), 9)))
        png.extend(chunk(b"IEND", b""))
        path.write_bytes(png)


FONT = PSFFont(FONT_PATH)


def label_box(
    c: Canvas,
    x: int,
    y: int,
    w: int,
    h: int,
    text: str,
    fill: Color,
    outline: Color = BLACK,
    scale: int = 1,
    text_color: Color = BLACK,
    border: int = 2,
) -> None:
    c.rect(x, y, w, h, fill=fill, outline=outline, border=border)
    c.text(x + w // 2, y + (h - FONT.measure(text, scale)[1]) // 2, text, FONT, color=text_color, scale=scale, align="center")


def section_title(c: Canvas, x: int, y: int, w: int, text: str) -> None:
    c.fill_rect(x, y, w, 28, WHITE)
    c.text(x + w // 2, y + 4, text, FONT, color=BLACK, scale=1, align="center")


def draw_feature_stack(c: Canvas, x: int, y: int, w: int, h: int, layers: int, label: str, fill: Color) -> None:
    for i in range(layers - 1, -1, -1):
        c.rect(x + i * 8, y - i * 6, w, h, fill=fill, outline=BLACK, border=2)
    c.text(x + w // 2 + 10, y + h // 2 - 12, label, FONT, color=BLACK, scale=1, align="center")


def draw_synthetic_scene(c: Canvas, x: int, y: int, w: int, h: int, with_marks: bool = False) -> None:
    c.rect(x, y, w, h, fill=LIGHT_GREY, outline=BLACK, border=2)
    c.fill_rect(x + 4, y + 4, w - 8, h - 8, Color(214, 222, 226))
    c.fill_rect(x + w // 2 - 18, y + 2, 36, h - 4, Color(154, 157, 160))
    c.fill_rect(x + w // 2 - 10, y + 2, 20, h - 4, Color(120, 125, 128))
    c.fill_rect(x + 8, y + 8, w // 2 - 20, h - 16, Color(127, 160, 110))
    c.fill_rect(x + w // 2 + 18, y + 8, w // 2 - 26, h - 16, Color(132, 166, 113))
    for yy in range(y + 10, y + h - 10, 16):
        c.fill_rect(x + w // 2 - 2, yy, 4, 8, WHITE)
    for xx in range(x + 16, x + w - 16, 18):
        c.line(xx, y + 12, xx - 6, y + h - 12, Color(98, 124, 90), 1)
        c.line(xx + 6, y + 12, xx, y + h - 12, Color(98, 124, 90), 1)
    if with_marks:
        marks = [
            (x + w - 44, y + 16, PATH_RED),
            (x + w - 34, y + 32, PATH_BLUE),
            (x + w - 56, y + 42, PATH_GOLD),
            (x + w - 26, y + 52, PATH_GREEN),
            (x + w - 48, y + 58, PATH_RED),
        ]
        for mx, my, col in marks:
            c.rect(mx, my, 18, 12, fill=WHITE, outline=col, border=2)


def draw_upsample_icon(c: Canvas, cx: int, cy: int, r: int = 12) -> None:
    c.circle(cx, cy, r, fill=WHITE, outline=BLACK)
    c.line(cx - 7, cy + 7, cx + 7, cy - 7, BLACK, 2)


def slanted_box(c: Canvas, x: int, y: int, w: int, h: int, skew: int, text: str, fill: Color, outline: Color = BLACK) -> None:
    for yy in range(h):
        left = x + int(skew * (h - yy - 1) / max(h - 1, 1))
        right = x + w + int(skew * (h - yy - 1) / max(h - 1, 1))
        c.fill_rect(left, y + yy, right - left, 1, fill)
    c.line(x + skew, y, x + w + skew, y, outline, 2)
    c.line(x, y + h, x + w, y + h, outline, 2)
    c.line(x + skew, y, x, y + h, outline, 2)
    c.line(x + w + skew, y, x + w, y + h, outline, 2)
    c.text(x + w // 2 + skew // 2, y + (h - FONT.measure(text, 1)[1]) // 2, text, FONT, color=BLACK, scale=1, align="center")


def draw_overall_figure(path: Path) -> None:
    c = Canvas(1700, 1080, WHITE)
    c.dashed_rect(24, 24, 1652, 1032, DASH_GREY)

    bb = (56, 116, 268, 742)
    nk = (350, 116, 860, 742)
    hd = (1234, 116, 390, 742)
    c.dashed_rect(*bb, DASH_GREY)
    c.dashed_rect(*nk, DASH_GREY)
    c.dashed_rect(*hd, DASH_GREY)

    c.text(bb[0] + bb[2] // 2, 70, "BACKBONE", FONT, scale=1, align="center")
    c.text(nk[0] + nk[2] // 2, 70, "NECK", FONT, scale=1, align="center")
    c.text(hd[0] + hd[2] // 2, 70, "HEAD", FONT, scale=1, align="center")

    draw_synthetic_scene(c, 134, 146, 114, 82, False)
    c.arrow(190, 228, 190, 260, BLACK, 3)

    stage_w = 130
    stage_h = 40
    stage_x = 124
    stage_ys = [262, 392, 522, 652]
    stage_names = ["P2", "P3", "P4", "P5"]

    for idx, (name, yy) in enumerate(zip(stage_names, stage_ys)):
        label_box(c, stage_x, yy, stage_w, stage_h, "3x3Conv", BLUE, border=1)
        label_box(c, stage_x, yy + 50, stage_w, stage_h, "AB-CGLU", PINK2, border=1)
        label_box(c, stage_x, yy + 100, stage_w, stage_h, "CoordAtt" if name in {"P2", "P3"} else "DCNv4", GREEN2 if name in {"P2", "P3"} else PEACH2, border=1)
        c.arrow(190, yy + stage_h, 190, yy + 50, BLACK, 2)
        c.arrow(190, yy + 50 + stage_h, 190, yy + 100, BLACK, 2)
        c.text(278, yy + 58, name, FONT, scale=1, align="center")
        if idx < len(stage_ys) - 1:
            c.arrow(190, yy + 140, 190, stage_ys[idx + 1], BLACK, 2)

    draw_synthetic_scene(c, 434, 154, 92, 78, False)
    label_box(c, 584, 254, 70, 32, "S5", YELLOW, border=1)
    c.poly_arrow([(526, 193), (618, 193), (618, 254)], PATH_GOLD, 2)

    for off in range(0, 84, 14):
        c.fill_rect(520 + off, 392, 9, 14, PATH_BLUE)
        c.fill_rect(520 + off, 482, 9, 14, PATH_BLUE)
    label_box(c, 520, 425, 186, 40, "AIFI", YELLOW2, border=1)

    feat_x = 540
    feat_y = 618
    draw_feature_stack(c, feat_x, feat_y + 118, 138, 34, 4, "P2", PATH_RED)
    draw_feature_stack(c, feat_x + 16, feat_y + 84, 126, 34, 4, "P3", PATH_BLUE)
    draw_feature_stack(c, feat_x + 32, feat_y + 50, 114, 34, 4, "P4", PATH_GREEN)
    draw_feature_stack(c, feat_x + 48, feat_y + 16, 102, 34, 4, "P5", PATH_GOLD)

    fusion_x = 790
    fusion_y = 238
    fusion_w = 338
    fusion_h = 454
    c.rect(fusion_x, fusion_y, fusion_w, fusion_h, fill=BLUE2, outline=LIGHT_GREY, border=1)
    label_box(c, 962, 286, 94, 32, "Fusion", LIGHT_GREY, border=1)
    label_box(c, 842, 434, 96, 40, "CSFF", YELLOW, border=1)
    label_box(c, 842, 558, 96, 40, "CSFF", YELLOW, border=1)
    label_box(c, 958, 430, 84, 32, "Fusion", LIGHT_GREY, border=1)
    label_box(c, 1058, 430, 84, 32, "Fusion", LIGHT_GREY, border=1)
    label_box(c, 958, 554, 84, 32, "Fusion", LIGHT_GREY, border=1)
    label_box(c, 1058, 554, 84, 32, "Fusion", LIGHT_GREY, border=1)
    label_box(c, 1152, 326, 84, 34, "MPFD", GREEN, border=1)
    label_box(c, 1152, 448, 84, 34, "MPFD", GREEN, border=1)
    label_box(c, 1152, 572, 84, 34, "MPFD", GREEN, border=1)

    c.poly_arrow([(654, 270), (962, 270), (962, 302)], PATH_GOLD, 3)
    c.poly_arrow([(706, 444), (842, 444)], PATH_BLUE, 3)
    c.poly_arrow([(680, 678), (772, 678), (772, 446), (842, 446)], PATH_GREEN, 3)
    c.poly_arrow([(652, 766), (752, 766), (752, 570), (842, 570)], PATH_RED, 3)
    c.poly_arrow([(652, 730), (736, 730), (736, 576), (842, 576)], PATH_BLUE, 2)

    c.poly_arrow([(1008, 318), (936, 318), (936, 638)], BLACK, 2)
    draw_upsample_icon(c, 936, 382, 12)
    draw_upsample_icon(c, 936, 504, 12)
    draw_upsample_icon(c, 936, 626, 12)
    c.poly_arrow([(948, 382), (948, 446), (958, 446)], BLACK, 2)
    c.poly_arrow([(948, 504), (948, 570), (958, 570)], BLACK, 2)

    c.arrow(938, 454, 958, 446, BLACK, 2)
    c.arrow(938, 578, 958, 570, BLACK, 2)
    c.arrow(1056, 302, 1152, 343, BLACK, 2)
    c.arrow(1042, 446, 1058, 446, BLACK, 2)
    c.arrow(1142, 446, 1152, 465, BLACK, 2)
    c.arrow(1042, 570, 1058, 570, BLACK, 2)
    c.arrow(1142, 570, 1152, 589, BLACK, 2)

    c.line(1236, 343, 1270, 343, BLACK, 2)
    c.line(1236, 465, 1270, 465, BLACK, 2)
    c.line(1236, 589, 1270, 589, BLACK, 2)
    c.line(1270, 343, 1270, 589, BLACK, 2)

    c.circle(1280, 466, 14, fill=WHITE, outline=BLACK)
    c.text(1280, 458, "C", FONT, scale=1, align="center")
    c.arrow(1294, 466, 1318, 466, BLACK, 3)

    for i in range(12):
        c.fill_rect(1276, 336 + i * 20, 8, 14, GREEN)
    slanted_box(c, 1310, 354, 90, 218, 18, "IOU\nQUERY\nSEL.", PEACH2)
    for i in range(10):
        c.fill_rect(1420, 374 + i * 17, 8, 12, ORANGE)
    slanted_box(c, 1452, 360, 108, 212, 20, "DECODER\nHEAD", BLUE)
    c.arrow(1412, 466, 1460, 466, BLACK, 3)
    c.arrow(1562, 466, 1600, 466, BLACK, 3)

    draw_synthetic_scene(c, 1514, 162, 88, 78, True)
    for i, col in enumerate([PATH_GOLD, PATH_RED, PATH_BLUE, PATH_GREEN]):
        c.poly_arrow([(1600, 466), (1622 + i * 4, 440 - i * 12), (1622 + i * 4, 246 - i * 10), (1602 - i * 2, 204 + i * 10)], col, 2)
    for i, col in enumerate([PATH_GREEN, PATH_RED, PATH_BLUE, PATH_GOLD]):
        c.fill_rect(1612, 328 + i * 17, 10, 12, col)

    c.text(bb[0] + bb[2] // 2, 888, "BACKBONE", FONT, scale=1, align="center")
    c.text(nk[0] + nk[2] // 2, 888, "NECK", FONT, scale=1, align="center")
    c.text(hd[0] + hd[2] // 2, 888, "HEAD", FONT, scale=1, align="center")

    legend = [
        (126, "AB-CGLU", PINK2, "LIGHT BLOCK"),
        (334, "CSFF", YELLOW, "SCALE FUSION"),
        (522, "MPFD", GREEN, "PATH FUSION"),
        (726, "COORDATT", GREEN2, "SMALL ATTN"),
    ]
    for cx, tag, fill, desc in legend:
        width = 132 if tag == "COORDATT" else 120
        label_box(c, cx - width // 2, 938, width, 36, tag, fill, border=1)
        c.text(cx, 982, desc, FONT, scale=1, align="center")
    draw_upsample_icon(c, 930, 956, 12)
    c.text(930, 982, "UPSAMPLE", FONT, scale=1, align="center")
    c.circle(1080, 956, 12, fill=WHITE, outline=BLACK)
    c.text(1080, 947, "C", FONT, scale=1, align="center")
    c.text(1080, 982, "CONCAT", FONT, scale=1, align="center")
    c.save_png(path)


def draw_module_composite(path: Path) -> None:
    c = Canvas(1240, 1700, WHITE)
    c.dashed_rect(20, 20, 1200, 1660, DASH_GREY)
    panels = {
        "A": (48, 76, 546, 728, "(a) AdditiveBlock"),
        "B": (646, 76, 546, 728, "(b) DySample"),
        "C": (48, 874, 546, 728, "(c) ASFF_V3"),
        "D": (646, 874, 546, 728, "(d) CoordAtt"),
    }
    for x, y, w, h, title in panels.values():
        c.rect(x, y, w, h, fill=WHITE, outline=LIGHT_GREY, border=1)
        c.text(x + w // 2, y + 18, title.upper(), FONT, scale=1, align="center")

    # (a) AdditiveBlock
    x, y, w, h, _ = panels["A"]
    c.rect(x + 116, y + 136, 330, 364, fill=YELLOW2, outline=LIGHT_GREY, border=1)
    draw_feature_stack(c, x + 38, y + 250, 92, 68, 3, "INPUT", BLUE2)
    label_box(c, x + 178, y + 168, 118, 70, "LOCAL\nDWCONV", GREEN2, border=1)
    label_box(c, x + 332, y + 168, 128, 70, "ADDITIVE\nMIXER", YELLOW, border=1)
    label_box(c, x + 250, y + 332, 138, 82, "CGLU\nGATE", PINK2, border=1)
    label_box(c, x + 438, y + 332, 70, 70, "OUT", BLUE2, border=1)
    c.arrow(x + 130, y + 284, x + 178, y + 203, BLACK, 2)
    c.arrow(x + 296, y + 203, x + 332, y + 203, BLACK, 2)
    c.arrow(x + 396, y + 238, x + 328, y + 332, BLACK, 2)
    c.arrow(x + 388, y + 373, x + 438, y + 367, BLACK, 2)
    c.line(x + 130, y + 284, x + 130, y + 367, BLACK, 2)
    c.line(x + 130, y + 367, x + 250, y + 367, BLACK, 2)
    c.circle(x + 418, y + 367, 11, fill=WHITE, outline=BLACK)
    c.text(x + 418, y + 360, "+", FONT, scale=1, align="center")
    c.line(x + 508, y + 367, x + 530, y + 367, BLACK, 2)
    c.text(x + 281, y + 544, "Q,K,V -> (Q+K) * DWCONV(V)", FONT, scale=1, align="center")
    c.text(x + 281, y + 588, "LOCAL DETAIL + TOKEN MIXING + GATED FEEDFORWARD", FONT, scale=1, align="center")

    # (b) DySample
    x, y, w, h, _ = panels["B"]
    c.rect(x + 132, y + 150, 292, 348, fill=BLUE2, outline=LIGHT_GREY, border=1)
    draw_feature_stack(c, x + 36, y + 250, 92, 70, 3, "INPUT", BLUE2)
    label_box(c, x + 178, y + 170, 118, 62, "OFFSET\n1X1 CONV", YELLOW2, border=1)
    label_box(c, x + 176, y + 330, 120, 58, "REF GRID", LIGHT_GREY, border=1)
    label_box(c, x + 336, y + 242, 132, 86, "GRID\nSAMPLE", GREEN2, border=1)
    draw_feature_stack(c, x + 388, y + 426, 98, 78, 3, "OUTPUT", BLUE2)
    c.arrow(x + 128, y + 286, x + 178, y + 201, BLACK, 2)
    c.arrow(x + 128, y + 286, x + 176, y + 359, BLACK, 2)
    c.arrow(x + 296, y + 201, x + 336, y + 278, BLACK, 2)
    c.arrow(x + 296, y + 359, x + 336, y + 300, BLACK, 2)
    c.arrow(x + 402, y + 328, x + 436, y + 426, BLACK, 2)
    for px, py in [(x + 228, y + 452), (x + 254, y + 438), (x + 286, y + 420), (x + 314, y + 406)]:
        c.circle(px, py, 4, fill=PATH_BLUE, outline=PATH_BLUE)
    c.poly_arrow([(x + 228, y + 452), (x + 264, y + 436), (x + 320, y + 382)], PATH_BLUE, 2)
    c.text(x + 273, y + 552, "OFFSET-GUIDED RESAMPLING", FONT, scale=1, align="center")
    c.text(x + 273, y + 594, "PRESERVE TINY OBJECT EDGES", FONT, scale=1, align="center")

    # (c) ASFF_V3
    x, y, w, h, _ = panels["C"]
    c.rect(x + 156, y + 132, 246, 430, fill=PEACH2, outline=LIGHT_GREY, border=1)
    rows = [("P2", BLUE2, 0), ("P3", GREEN2, 94), ("P4", YELLOW2, 188), ("P5", PINK2, 282)]
    for name, fill, yy in rows:
        label_box(c, x + 40, y + 176 + yy, 88, 50, name, fill, border=1)
        label_box(c, x + 176, y + 176 + yy, 92, 50, "ALIGN", LIGHT_GREY, border=1)
        label_box(c, x + 306, y + 176 + yy, 92, 50, "W_" + name, MINT, border=1)
        c.arrow(x + 128, y + 201 + yy, x + 176, y + 201 + yy, BLACK, 2)
        c.arrow(x + 268, y + 201 + yy, x + 306, y + 201 + yy, BLACK, 2)
    c.circle(x + 470, y + 356, 14, fill=WHITE, outline=BLACK)
    c.text(x + 470, y + 347, "Σ", FONT, scale=1, align="center")
    for _, _, yy in rows:
        c.poly_arrow([(x + 398, y + 201 + yy), (x + 438, y + 201 + yy), (x + 438, y + 356), (x + 456, y + 356)], BLACK, 2)
    label_box(c, x + 412, y + 472, 118, 64, "SOFTMAX\nWEIGHTS", PEACH, border=1)
    label_box(c, x + 398, y + 610, 146, 70, "EXPAND\nFUSED OUT", PURPLE, border=1)
    c.arrow(x + 470, y + 370, x + 470, y + 472, BLACK, 2)
    c.arrow(x + 470, y + 536, x + 470, y + 610, BLACK, 2)
    c.text(x + 274, y + 726, "ALIGN MULTI-SCALE FEATURES AND LEARN PIXEL-WISE FUSION WEIGHTS", FONT, scale=1, align="center")

    # (d) CoordAtt
    x, y, w, h, _ = panels["D"]
    c.rect(x + 120, y + 146, 318, 430, fill=GREEN2, outline=LIGHT_GREY, border=1)
    draw_feature_stack(c, x + 40, y + 292, 90, 70, 3, "INPUT", BLUE2)
    label_box(c, x + 176, y + 188, 104, 58, "H-POOL", GREEN2, border=1)
    label_box(c, x + 176, y + 392, 104, 58, "W-POOL", GREEN2, border=1)
    label_box(c, x + 318, y + 286, 144, 82, "CONCAT\n1X1 CONV\nH-SWISH", YELLOW2, border=1)
    label_box(c, x + 322, y + 138, 116, 56, "CONV_H", PINK2, border=1)
    label_box(c, x + 322, y + 458, 116, 56, "CONV_W", PINK2, border=1)
    c.circle(x + 492, y + 242, 11, fill=WHITE, outline=BLACK)
    c.text(x + 492, y + 235, "×", FONT, scale=1, align="center")
    c.circle(x + 492, y + 472, 11, fill=WHITE, outline=BLACK)
    c.text(x + 492, y + 465, "×", FONT, scale=1, align="center")
    label_box(c, x + 440, y + 608, 86, 58, "OUT", BLUE2, border=1)
    c.arrow(x + 130, y + 328, x + 176, y + 217, BLACK, 2)
    c.arrow(x + 130, y + 328, x + 176, y + 421, BLACK, 2)
    c.arrow(x + 280, y + 217, x + 318, y + 319, BLACK, 2)
    c.arrow(x + 280, y + 421, x + 318, y + 333, BLACK, 2)
    c.arrow(x + 390, y + 286, x + 382, y + 194, BLACK, 2)
    c.arrow(x + 390, y + 368, x + 382, y + 458, BLACK, 2)
    c.poly_arrow([(x + 438, y + 166), (x + 492, y + 166), (x + 492, y + 231)], BLACK, 2)
    c.poly_arrow([(x + 438, y + 486), (x + 492, y + 486), (x + 492, y + 483)], BLACK, 2)
    c.poly_arrow([(x + 130, y + 328), (x + 130, y + 637), (x + 440, y + 637)], BLACK, 2)
    c.poly_arrow([(x + 503, y + 242), (x + 530, y + 242), (x + 530, y + 637), (x + 526, y + 637)], BLACK, 2)
    c.poly_arrow([(x + 503, y + 472), (x + 520, y + 472), (x + 520, y + 637), (x + 526, y + 637)], BLACK, 2)
    c.text(x + 274, y + 726, "ENCODE DIRECTION-AWARE POSITION INFORMATION", FONT, scale=1, align="center")

    c.save_png(path)


def draw_loss_figure(path: Path) -> None:
    c = Canvas(1160, 900, WHITE)
    c.dashed_rect(20, 20, 1120, 860, DASH_GREY)
    reg = (52, 94, 488, 560)
    cls = (620, 94, 488, 560)
    total = (274, 700, 612, 118)
    c.dashed_rect(*reg, DASH_GREY)
    c.dashed_rect(*cls, DASH_GREY)
    c.rect(*total, fill=WHITE, outline=LIGHT_GREY, border=1)
    c.text(reg[0] + reg[2] // 2, 62, "REGRESSION BRANCH", FONT, scale=1, align="center")
    c.text(cls[0] + cls[2] // 2, 62, "CLASSIFICATION BRANCH", FONT, scale=1, align="center")
    c.text(total[0] + total[2] // 2, 668, "TOTAL LOSS", FONT, scale=1, align="center")

    # regression path
    label_box(c, 86, 154, 128, 62, "PRED BOX", BLUE2, border=1)
    label_box(c, 86, 294, 128, 62, "GT BOX", GREEN2, border=1)
    label_box(c, 268, 144, 142, 72, "INNER BOX\nSCALE r", YELLOW2, border=1)
    label_box(c, 268, 286, 142, 72, "GAUSSIAN\nMAP", PINK2, border=1)
    label_box(c, 448, 144, 130, 72, "INNER-IOU", YELLOW, border=1)
    label_box(c, 448, 286, 130, 72, "NWD", PINK2, border=1)
    c.arrow(214, 185, 268, 180, BLACK, 2)
    c.arrow(214, 325, 268, 322, BLACK, 2)
    c.arrow(410, 180, 448, 180, BLACK, 2)
    c.arrow(410, 322, 448, 322, BLACK, 2)
    label_box(c, 252, 448, 232, 80, "Lreg = eta * Linner +\n(1-eta) * Lnwd", PEACH2, border=1)
    c.arrow(512, 216, 386, 448, BLACK, 2)
    c.arrow(512, 358, 386, 448, BLACK, 2)
    # inset
    c.rect(86, 438, 118, 84, fill=WHITE, outline=LIGHT_GREY, border=1)
    c.rect(110, 454, 64, 44, fill=WHITE, outline=PATH_BLUE, border=1)
    c.rect(126, 466, 32, 20, fill=WHITE, outline=PATH_RED, border=1)
    c.text(145, 534, "INNER-IoU", FONT, scale=1, align="center")

    # classification path
    label_box(c, 662, 146, 134, 62, "PRED SCORE", BLUE2, border=1)
    label_box(c, 662, 276, 134, 62, "QUALITY\nLABEL", GREEN2, border=1)
    label_box(c, 662, 406, 134, 62, "ONE-HOT y", GREEN2, border=1)
    slanted_box(c, 866, 224, 146, 168, 18, "EMA-SVFL\nCLASS LOSS", PURPLE)
    c.arrow(796, 176, 880, 258, BLACK, 2)
    c.arrow(796, 307, 880, 307, BLACK, 2)
    c.arrow(796, 437, 880, 356, BLACK, 2)
    for i in range(8):
        c.fill_rect(826, 210 + i * 22, 8, 12, ORANGE)
    c.text(864, 492, "QUALITY-AWARE CLASSIFICATION", FONT, scale=1, align="center")

    # total
    label_box(c, 474, 726, 212, 72, "L = lambda1 * Lreg\n+ lambda2 * Lcls", MINT, border=1)
    c.arrow(368, 528, 512, 726, BLACK, 2)
    c.arrow(940, 392, 650, 726, BLACK, 2)

    c.save_png(path)


def copy_ppr(p: ET.Element) -> ET.Element | None:
    ppr = p.find("w:pPr", NS)
    return copy.deepcopy(ppr) if ppr is not None else None


def make_paragraph_from_template(text: str, ppr_template: ET.Element | None) -> ET.Element:
    p = ET.Element(qn(W_NS, "p"))
    if ppr_template is not None:
        p.append(copy.deepcopy(ppr_template))
    r = ET.SubElement(p, qn(W_NS, "r"))
    t = ET.SubElement(r, qn(W_NS, "t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return p


def make_section_break_paragraph(sectpr: ET.Element) -> ET.Element:
    p = ET.Element(qn(W_NS, "p"))
    ppr = ET.SubElement(p, qn(W_NS, "pPr"))
    ET.SubElement(ppr, qn(W_NS, "ind"), {qn(W_NS, "firstLine"): "0"})
    ppr.append(copy.deepcopy(sectpr))
    return p


def make_center_image_paragraph(rel_id: str, name: str, cx: int, cy: int, docpr_id: int) -> ET.Element:
    p = ET.Element(qn(W_NS, "p"))
    ppr = ET.SubElement(p, qn(W_NS, "pPr"))
    ET.SubElement(ppr, qn(W_NS, "ind"), {qn(W_NS, "firstLine"): "0"})
    ET.SubElement(ppr, qn(W_NS, "jc"), {qn(W_NS, "val"): "center"})
    r = ET.SubElement(p, qn(W_NS, "r"))
    drawing = ET.SubElement(r, qn(W_NS, "drawing"))
    inline = ET.SubElement(drawing, qn(WP_NS, "inline"), {"distT": "0", "distB": "0", "distL": "0", "distR": "0"})
    ET.SubElement(inline, qn(WP_NS, "extent"), {"cx": str(cx), "cy": str(cy)})
    ET.SubElement(inline, qn(WP_NS, "effectExtent"), {"l": "0", "t": "0", "r": "0", "b": "0"})
    ET.SubElement(inline, qn(WP_NS, "docPr"), {"id": str(docpr_id), "name": name})
    cNv = ET.SubElement(inline, qn(WP_NS, "cNvGraphicFramePr"))
    ET.SubElement(cNv, qn(A_NS, "graphicFrameLocks"), {"noChangeAspect": "1"})
    graphic = ET.SubElement(inline, qn(A_NS, "graphic"))
    gdata = ET.SubElement(graphic, qn(A_NS, "graphicData"), {"uri": "http://schemas.openxmlformats.org/drawingml/2006/picture"})
    pic = ET.SubElement(gdata, qn(PIC_NS, "pic"))
    nv = ET.SubElement(pic, qn(PIC_NS, "nvPicPr"))
    ET.SubElement(nv, qn(PIC_NS, "cNvPr"), {"id": "0", "name": name})
    ET.SubElement(nv, qn(PIC_NS, "cNvPicPr"))
    blip_fill = ET.SubElement(pic, qn(PIC_NS, "blipFill"))
    ET.SubElement(blip_fill, qn(A_NS, "blip"), {qn(R_NS, "embed"): rel_id})
    stretch = ET.SubElement(blip_fill, qn(A_NS, "stretch"))
    ET.SubElement(stretch, qn(A_NS, "fillRect"))
    sppr = ET.SubElement(pic, qn(PIC_NS, "spPr"))
    xfrm = ET.SubElement(sppr, qn(A_NS, "xfrm"))
    ET.SubElement(xfrm, qn(A_NS, "off"), {"x": "0", "y": "0"})
    ET.SubElement(xfrm, qn(A_NS, "ext"), {"cx": str(cx), "cy": str(cy)})
    prst = ET.SubElement(sppr, qn(A_NS, "prstGeom"), {"prst": "rect"})
    ET.SubElement(prst, qn(A_NS, "avLst"))
    return p


def replace_first_run_text(p: ET.Element, text: str) -> None:
    for child in list(p):
        if child.tag != qn(W_NS, "pPr"):
            p.remove(child)
    r = ET.SubElement(p, qn(W_NS, "r"))
    t = ET.SubElement(r, qn(W_NS, "t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def ensure_png_content_type(ct_root: ET.Element) -> None:
    for child in ct_root.findall("ct:Default", NS):
        if child.get("Extension") == "png":
            return
    default = ET.Element(qn(CT_NS, "Default"), {"Extension": "png", "ContentType": "image/png"})
    ct_root.insert(1, default)


def next_rid(rels_root: ET.Element) -> int:
    max_id = 0
    for rel in rels_root.findall("rel:Relationship", NS):
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            max_id = max(max_id, int(rid[3:]))
    return max_id + 1


def remove_appendix(children: list[ET.Element]) -> list[ET.Element]:
    result = []
    skip = False
    for child in children:
        if child.tag == qn(W_NS, "p"):
            txt = strip_ws(get_text(child))
            if txt.startswith("附录A"):
                skip = True
        if not skip:
            result.append(child)
    return result


def insert_after_marker(children: list[ET.Element], marker: str, new_nodes: Iterable[ET.Element]) -> list[ET.Element]:
    result = []
    inserted = False
    for child in children:
        result.append(child)
        if not inserted and child.tag == qn(W_NS, "p") and strip_ws(get_text(child)) == marker:
            result.extend(copy.deepcopy(node) for node in new_nodes)
            inserted = True
    if not inserted:
        raise ValueError(f"Marker not found: {marker}")
    return result


def update_docx(figures: dict[str, Path]) -> None:
    with ZipFile(DOCX_IN) as zin:
        doc_root = ET.fromstring(zin.read("word/document.xml"))
        rels_root = ET.fromstring(zin.read("word/_rels/document.xml.rels"))
        ct_root = ET.fromstring(zin.read("[Content_Types].xml"))

        body = doc_root.find("w:body", NS)
        if body is None:
            raise ValueError("word/document.xml has no body")
        final_sectpr = copy.deepcopy(body[-1])
        children = [copy.deepcopy(ch) for ch in list(body[:-1])]
        one_col_sectpr = copy.deepcopy(final_sectpr)
        two_col_sectpr = None
        for child in children:
            if child.tag != qn(W_NS, "p"):
                continue
            ppr = child.find("w:pPr", NS)
            if ppr is None:
                continue
            sectpr = ppr.find("w:sectPr", NS)
            if sectpr is None:
                continue
            cols = sectpr.find("w:cols", NS)
            if cols is not None and cols.get(qn(W_NS, "num"), "1") == "2":
                two_col_sectpr = copy.deepcopy(sectpr)
        if two_col_sectpr is None:
            raise ValueError("Failed to locate two-column section settings")

        cn_cap_ppr = None
        en_cap_ppr = None
        for child in children:
            if child.tag != qn(W_NS, "p"):
                continue
            txt = strip_ws(get_text(child))
            if txt == "图1 改进 RT-DETR 小目标检测网络整体结构":
                cn_cap_ppr = copy_ppr(child)
            elif txt.startswith("Fig.1 "):
                en_cap_ppr = copy_ppr(child)
        if cn_cap_ppr is None or en_cap_ppr is None:
            raise ValueError("Failed to locate figure caption templates")

        # Update in-text references.
        for child in children:
            if child.tag != qn(W_NS, "p"):
                continue
            text = strip_ws(get_text(child))
            if text == "模块结构示意如图2所示。":
                replace_first_run_text(child, "AdditiveBlock 结构如图2(a)所示。")
            elif text.endswith("在小目标边缘保留方面表现更优。"):
                replace_first_run_text(
                    child,
                    text[:-1] + "，其结构示意如图2(b)所示。",
                )
            elif text.endswith("有效缓解多尺度语义冲突。"):
                replace_first_run_text(
                    child,
                    text[:-1] + "，融合结构如图2(c)所示。",
                )
            elif "模块结构如图3所示" in text:
                replace_first_run_text(child, text.replace("图3", "图2(d)"))

        # Remove old figure-2 and figure-3 caption placeholders; keep figure 1.
        filtered = []
        for child in children:
            if child.tag == qn(W_NS, "p"):
                txt = strip_ws(get_text(child))
                if txt in {
                    "图2 C2f-AdditiveBlock-CGLU 模块结构示意图",
                    "Fig.2 Schematic of the C2f-AdditiveBlock-CGLU module",
                    "图3 CoordAtt 坐标注意力模块结构示意图",
                    "Fig.3 Schematic of the CoordAtt module",
                }:
                    continue
            filtered.append(child)
        children = filtered

        # Add summary sentence before section 3.
        extra_sentence = make_paragraph_from_template(
            "综合考虑组合回归与分类分支，本文最终损失设计结构如图3所示。",
            None,
        )

        # Add new image relationships.
        rid_start = next_rid(rels_root)
        rel_ids = {}
        media_items = []
        for idx, (key, path) in enumerate(figures.items(), start=0):
            rid = f"rId{rid_start + idx}"
            rel_ids[key] = rid
            ET.SubElement(
                rels_root,
                qn(REL_NS, "Relationship"),
                {
                    "Id": rid,
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                    "Target": f"media/{path.name}",
                },
            )
            media_items.append((f"word/media/{path.name}", path.read_bytes()))

        ensure_png_content_type(ct_root)

        # Build image paragraphs and captions.
        fig1_img = make_center_image_paragraph(rel_ids["fig1"], "fig1_overall.png", int(6.20 * 914400), int(4.30 * 914400), 1)
        fig2_img = make_center_image_paragraph(rel_ids["fig2"], "fig2_modules.png", int(5.00 * 914400), int(6.95 * 914400), 2)
        fig3_img = make_center_image_paragraph(rel_ids["fig3"], "fig3_loss.png", int(5.70 * 914400), int(4.62 * 914400), 3)
        break_to_one_col = make_section_break_paragraph(two_col_sectpr)
        break_back_to_two_col = make_section_break_paragraph(one_col_sectpr)

        fig2_cn = make_paragraph_from_template(
            "图2 关键模块结构示意图：（a）AdditiveBlock；（b）DySample；（c）ASFF_V3；（d）CoordAtt",
            cn_cap_ppr,
        )
        fig2_en = make_paragraph_from_template(
            "Fig.2 Core module structures: (a) AdditiveBlock; (b) DySample; (c) ASFF_V3; (d) CoordAtt",
            en_cap_ppr,
        )
        fig3_cn = make_paragraph_from_template("图3 小目标损失函数设计结构图", cn_cap_ppr)
        fig3_en = make_paragraph_from_template("Fig.3 Structure of the small-target loss design", en_cap_ppr)

        children = remove_appendix(children)
        children = insert_after_marker(
            children,
            "检测头与损失：RTDETRDecoder 接收四尺度融合特征，采用 300 个查询向量；回归损失采用 Inner-IoU 与 NWD 的加权组合，分类损失采用 EMA-SVFL。",
            [break_to_one_col, fig1_img],
        )
        children = insert_after_marker(
            children,
            "Fig.1 Overall architecture of the enhanced RT-DETR small object detection network",
            [break_back_to_two_col],
        )
        children = insert_after_marker(
            children,
            "其中 $\\delta$ 为 h-swish 激活函数，$\\sigma$ 为 Sigmoid 函数。该机制以较低计算代价在复杂背景中突出与目标位置相关的特征区域，模块结构如图2(d)所示。",
            [break_to_one_col, fig2_img, fig2_cn, fig2_en, break_back_to_two_col],
        )
        children = insert_after_marker(
            children,
            "其中 $p$ 为预测得分，$q$ 为 IoU 质量感知标签，$y$ 为 one-hot 类别标记，$\\alpha = 0.6$，$\\gamma = 1.5$。EMA 机制通过指数滑动平均稳定质量标签估计，减少训练初期噪声标签的影响。",
            [extra_sentence, break_to_one_col, fig3_img, fig3_cn, fig3_en, break_back_to_two_col],
        )

        # Rebuild body.
        for child in list(body):
            body.remove(child)
        for child in children:
            body.append(child)
        body.append(final_sectpr)

        document_xml = ET.tostring(doc_root, encoding="utf-8", xml_declaration=True)
        rels_xml = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
        ct_xml = ET.tostring(ct_root, encoding="utf-8", xml_declaration=True)

        with ZipFile(DOCX_OUT, "w", compression=ZIP_DEFLATED) as zout:
            existing_media = {name for name, _ in media_items}
            for item in zin.infolist():
                if item.filename == "word/document.xml":
                    zout.writestr(item, document_xml)
                elif item.filename == "word/_rels/document.xml.rels":
                    zout.writestr(item, rels_xml)
                elif item.filename == "[Content_Types].xml":
                    zout.writestr(item, ct_xml)
                elif item.filename in existing_media:
                    continue
                elif item.filename.startswith("word/media/") and item.filename.endswith("/"):
                    zout.writestr(item, zin.read(item.filename))
                else:
                    zout.writestr(item, zin.read(item.filename))
            for name, data in media_items:
                zout.writestr(name, data)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    figs = {
        "fig1": FIG_DIR / "fig1_overall.png",
        "fig2": FIG_DIR / "fig2_modules.png",
        "fig3": FIG_DIR / "fig3_loss.png",
    }
    draw_overall_figure(figs["fig1"])
    draw_module_composite(figs["fig2"])
    draw_loss_figure(figs["fig3"])
    update_docx(figs)
    print(DOCX_OUT)


if __name__ == "__main__":
    main()
