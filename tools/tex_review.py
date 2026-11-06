# -*- coding: utf-8 -*-
"""그림 선별용 시트(2026-11-05). 글자판 점수·OCR 일본어 후보를 합쳐 눈으로 볼 시트를 만든다(읽기만, 원본·디스크 안 건드림).
  → work/tex/review/<UI|WORLD>_NN.png  칸 = 번호·id 앞 8자(★라벨은 그림 바로 위), review/ids.tsv = 번호→전체 id·분류·점수·OCR·1편 처리 여부
  python tools/tex_review.py
"""
import os, re, sys, glob
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'work', 'tex'); R = os.path.join(T, 'review'); os.makedirs(R, exist_ok=True)
S1 = os.path.join(os.path.dirname(ROOT), 'shenmue-kr-patch', 'work', 'scene_tex', 'new')
idx = {}
for l in open(os.path.join(T, 'index.tsv'), encoding='utf-8').read().splitlines()[1:]:
    c = l.split('\t'); idx[c[0]] = c
score = {}
for l in open(os.path.join(T, 'textlike.tsv'), encoding='utf-8').read().splitlines():
    c = l.split('\t')
    if len(c) >= 2:
        try: score[c[1]] = float(c[0])
        except ValueError: pass
ocr = {}
for l in open(os.path.join(T, 'ocr.tsv'), encoding='utf-8').read().splitlines()[1:]:
    c = l.split('\t', 1)
    if len(c) == 2: ocr[c[0]] = c[1]
JA = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
def ja(t):  # OCR 결과에 일본어 글자가 2자 이상
    return len(JA.findall(t)) >= 2
done1 = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(S1, '*.png'))}
UI = ('SPRITE', 'MISC', 'ROOT', 'TITLE', 'EVENT')
def is_ui(k):
    s = idx[k][7]
    return idx[k][6] in UI
ui =[k for k in idx if is_ui(k)]
world = [k for k in idx if k not in set(ui) and (score.get(k, 0) >= 0.2 or ja(ocr.get(k, '')))]
world.sort(key=lambda k: (-max(score.get(k, 0), 0.6 if ja(ocr.get(k, '')) else 0), k))
f = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 11)
C, N = 12, 10
out = ['no\tid\tset\tw\th\tgroup\tscore\tocr\tshenmue1_done']
def sheets(ids, name, start):
    for p in range(0, len(ids), C * N):
        sh = Image.new('RGB', (C * 120, N * 132), (32, 32, 38)); d = ImageDraw.Draw(sh)
        for i, k in enumerate(ids[p:p + C * N]):
            im = Image.open(os.path.join(T, 'png', k + '.png')).convert('RGBA'); w, h = im.size
            s = min(116 / w, 116 / h); im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.NEAREST if s >= 1 else Image.LANCZOS)
            bg = Image.new('RGBA', im.size, (128, 128, 128, 255)); bg.alpha_composite(im)
            x, y = (i % C) * 120, (i // C) * 132; no = start + p + i
            d.text((x + 2, y), '%d %s' % (no, k[:8]), font=f, fill=(120, 255, 120) if k in done1 else (255, 220, 90))
            sh.paste(bg.convert('RGB'), (x + 2, y + 15))
            out.append('\t'.join([str(no), k, name, idx[k][1], idx[k][2], idx[k][6], '%.3f' % score.get(k, 0), ocr.get(k, '').replace('\t', ' ')[:80], '1' if k in done1 else '']))
        sh.save(os.path.join(R, '%s_%02d.png' % (name, p // (C * N))))
    return start + len(ids)
n = sheets(ui, 'UI', 0)
n = sheets(world, 'WORLD', n)
open(os.path.join(R, 'ids.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('전체', len(idx), 'UI', len(ui), 'WORLD 후보', len(world), '1편 처리와 같은 id', len(done1 & set(idx)))
