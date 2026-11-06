# -*- coding: utf-8 -*-
"""OCR 입력 만들기: work/tex/png → work/tex/ocr_in (회색 바탕 합성, 2000px 까지 확대) — 쉔무 1 과 같은 방식"""
import os, glob
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(ROOT, 'work', 'tex', 'png'); dst = os.path.join(ROOT, 'work', 'tex', 'ocr_in'); os.makedirs(dst, exist_ok=True)
for p in sorted(glob.glob(src + '/*.png')):
    im = Image.open(p).convert('RGBA'); w, h = im.size
    if w < 16 or h < 16: continue
    bg = Image.new('RGBA', im.size, (128, 128, 128, 255)); bg.alpha_composite(im)
    s = max(1, min(4, 2000 // max(w, h)))
    bg.convert('RGB').resize((w * s, h * s), Image.LANCZOS).save(os.path.join(dst, os.path.basename(p)))
