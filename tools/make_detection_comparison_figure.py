import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from ultralytics import RTDETR


DEFAULT_BASELINE = "/home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/runs/train/rtdetr-r18/weights/best.pt"
DEFAULT_OURS = "/home/rtdetr/project/RTDETR-20251122/RTDETR-20251122/RTDETR-main/runs/train/rtdetr-DSDC-SPAFM-SAIW/weights/best.pt"
DEFAULT_SOURCE = "/home/rtdetr/project/visdrone2019/VisDrone2019-DET-test-dev/images"
DEFAULT_OUTPUT = "runs/visualization/visdrone2019/fig_detection_compare.png"

DEFAULT_SCENES = [
    "模糊画面",
    "夜间弱光环境",
    "夜间强光环境",
    "遮挡画面",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a paper-style two-column detection comparison figure."
    )
    parser.add_argument("--baseline", default=DEFAULT_BASELINE, help="Baseline weight path.")
    parser.add_argument("--ours", default=DEFAULT_OURS, help="Proposed model weight path.")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Image directory or comma-separated image paths.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output figure path.")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size.")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--max-images", type=int, default=5, help="Number of rows in the figure.")
    parser.add_argument(
        "--scenes",
        default=",".join(DEFAULT_SCENES),
        help="Comma-separated captions, one for each image row.",
    )
    parser.add_argument("--left-title", default="RT-DETR-r18", help="Left column title.")
    parser.add_argument("--right-title", default="DSS-RTDETR", help="Right column title.")
    parser.add_argument("--font", default="", help="Optional font path for Chinese captions.")
    parser.add_argument("--line-width", type=int, default=2, help="Detection box line width.")
    return parser.parse_args()


def find_font(user_font=""):
    candidates = [
        user_font,
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for item in candidates:
        if item and Path(item).exists():
            return item
    return ""


def load_font(path, size):
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def resolve_images(source, max_images):
    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    if "," in source:
        images = [Path(item.strip()) for item in source.split(",") if item.strip()]
    else:
        path = Path(source)
        if path.is_dir():
            images = sorted(p for p in path.iterdir() if p.suffix.lower() in image_exts)
        else:
            images = [path]
    images = [p for p in images if p.exists()]
    if not images:
        raise FileNotFoundError(f"No images found from source: {source}")
    return images[:max_images]


def predict_image(model, image_path, imgsz, conf, line_width):
    result = model.predict(
        source=str(image_path),
        imgsz=imgsz,
        conf=conf,
        save=False,
        verbose=False,
        line_width=line_width,
    )[0]
    plotted = result.plot(line_width=line_width)
    return Image.fromarray(plotted).convert("RGB")


def resize_to_width(image, width):
    ratio = width / image.width
    height = int(round(image.height * ratio))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def draw_centered_text(draw, xy, width, text, font, fill=(0, 0, 0)):
    left, top = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text((left + (width - text_w) / 2, top), text, font=font, fill=fill)


def make_figure(pairs, scenes, output, left_title, right_title, font_path):
    column_width = 640
    gap = 30
    margin_x = 40
    margin_y = 26
    title_h = 42
    caption_h = 42
    row_gap = 18

    title_font = load_font(font_path, 24)
    caption_font = load_font(font_path, 22)

    rows = []
    for idx, (left_img, right_img) in enumerate(pairs):
        left_img = resize_to_width(left_img, column_width)
        right_img = resize_to_width(right_img, column_width)
        row_h = max(left_img.height, right_img.height)

        row = Image.new("RGB", (column_width * 2 + gap, row_h + caption_h), "white")
        row.paste(left_img, (0, 0))
        row.paste(right_img, (column_width + gap, 0))

        draw = ImageDraw.Draw(row)
        label = f"({chr(ord('a') + idx)}) {scenes[idx] if idx < len(scenes) else f'Scene {idx + 1}'}"
        draw_centered_text(draw, (0, row_h + 7), row.width, label, caption_font)
        rows.append(row)

    figure_w = margin_x * 2 + column_width * 2 + gap
    figure_h = margin_y * 2 + title_h + sum(row.height for row in rows) + row_gap * (len(rows) - 1)
    figure = Image.new("RGB", (figure_w, figure_h), "white")
    draw = ImageDraw.Draw(figure)

    x0 = margin_x
    y = margin_y
    draw_centered_text(draw, (x0, y), column_width, left_title, title_font)
    draw_centered_text(draw, (x0 + column_width + gap, y), column_width, right_title, title_font)
    y += title_h

    for row in rows:
        figure.paste(row, (x0, y))
        y += row.height + row_gap

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.save(output)
    return output


def main():
    args = parse_args()
    images = resolve_images(args.source, args.max_images)
    scenes = [item.strip() for item in args.scenes.split(",") if item.strip()]
    font_path = find_font(args.font)

    baseline = RTDETR(args.baseline)
    ours = RTDETR(args.ours)

    pairs = []
    for image_path in images:
        baseline_img = predict_image(baseline, image_path, args.imgsz, args.conf, args.line_width)
        ours_img = predict_image(ours, image_path, args.imgsz, args.conf, args.line_width)
        pairs.append((baseline_img, ours_img))

    output = make_figure(pairs, scenes, args.output, args.left_title, args.right_title, font_path)
    print(f"Saved comparison figure to: {output}")


if __name__ == "__main__":
    main()
