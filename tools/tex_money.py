# -*- coding: utf-8 -*-
"""소지품 창 숫자 판(MISC/TEXTURES.PKS, b2001785ce28) 낱칸 — 枚→개 · 元→원. 1편 gfx_jobs_misc 의 円→엔·枚→개 와 같은 칸 처리.
  칸 16×16, 회색 글자 + 진한 검은 테두리(하스피: 첫 판 + 테두리만 진하게).
  python tools/tex_money.py → work/tex/new/b2001785ce28.png
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import tex_auto as X

ID = 'b2001785ce28'
CELLS = (((112, 80, 128, 96), '개'), ((112, 112, 128, 128), '원'))
T = os.path.join(ROOT, 'work', 'tex')

def main():
    A = np.array(Image.open(os.path.join(T, 'png', ID + '.png')).convert('RGBA'))
    for (x0, y0, x1, y1), t in CELLS:
        L = np.zeros((16, 16, 4), np.uint8)
        m = X.text_mask((16, 16), [(t, 7.5, 7.5)], 'heavy', 13)
        X.paint(L, np.clip(X.outline(m, 1) * 4, 0, 1), (0, 0, 0), True); X.paint(L, m, (136, 136, 136), True)
        A[y0:y1, x0:x1] = L
    Image.fromarray(A).save(os.path.join(T, 'new', ID + '.png'))

if __name__ == '__main__':
    main()
