#!/usr/bin/env python3
"""Extract document content to a text file for analysis."""
from docx import Document
import os

doc_path = "/root/autodl-tmp/paper/my article/DSS-RTDETR：增强型航拍小目标检测算法.docx"
out_path = "/root/autodl-tmp/paper/_paper_content.txt"

doc = Document(doc_path)

with open(out_path, 'w', encoding='utf-8') as f:
    # Write paragraphs
    f.write("=" * 80 + "\n")
    f.write("PAPER CONTENT - ALL PARAGRAPHS\n")
    f.write("=" * 80 + "\n\n")
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            f.write(f"[P{i}] {text}\n\n")
    
    # Write tables
    f.write("\n\n" + "=" * 80 + "\n")
    f.write("TABLES\n")
    f.write("=" * 80 + "\n\n")
    for ti, table in enumerate(doc.tables):
        f.write(f"\n--- Table {ti} ---\n")
        for ri, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            f.write(f"  Row {ri}: {' | '.join(cells)}\n")
        f.write("\n")

print(f"Written to {out_path}")
print(f"File size: {os.path.getsize(out_path)} bytes")
