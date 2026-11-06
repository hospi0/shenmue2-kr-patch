# -*- coding: utf-8 -*-
"""채진가 안내도의 이름 판(6b85b0c67059, WS00MM*.MT7 — 지도 + 글자판 + 이 판 3장 조립). 한자 칸만 지우고 영문 줄은 원본 유지.
  게임이 칸을 잘라 붙이므로 글자는 원본 칸 범위 안에. 표기 = 대사·다른 지도 그림과 같게.
  python tools/tex_signmap.py → work/tex/new/6b85b0c67059.png
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import tex_auto as X

ID = '6b85b0c67059'
T = os.path.join(ROOT, 'work', 'tex')
CELLS = (((2, 1, 76, 18), '건강정육점'), ((180, 1, 254, 18), '방래여사'),
         ((2, 34, 84, 50), '태산식료품'), ((180, 34, 254, 50), '채진전당포'),
         ((2, 66, 61, 82), '천과일'), ((158, 66, 234, 82), '선경점집'),
         ((2, 98, 76, 114), '길상정육점'), ((163, 98, 254, 114), '미우식료품'),
         ((3, 129, 77, 146), '광동찻집'), ((134, 129, 222, 146), '채진조미품'),
         ((2, 162, 76, 178), '문무주점'), ((145, 162, 220, 178), '영년채소점'),
         ((24, 195, 79, 211), '천향찻집'), ((179, 195, 254, 211), '낙연찻집'),
         ((2, 227, 60, 243), '석죽화'), ((86, 227, 161, 243), '오슈 소바'), ((173, 227, 250, 243), '일본 소바'))

def main():
    A = np.array(Image.open(os.path.join(T, 'png', ID + '.png')).convert('RGBA'))
    for (x0, y0, x1, y1), t in CELLS:
        A[max(0, y0 - 2):y1 + 1, x0:x1 + 1] = 0            # 원본 글자 윗줄 테두리까지
        l = '[%s]' % t
        size = X.fit_size([l], 'gothic_b', x1 - x0 - 2, y1 - y0 - 1)
        m = X.text_mask(A.shape[:2], [(l, (x0 + x1) / 2, (y0 + y1) / 2)], 'gothic_b', size)
        X.paint(A, np.clip(X.outline(m, 1) * 3, 0, 1), (255, 255, 255), True); X.paint(A, m, (0, 0, 0), True)
    Image.fromarray(A).save(os.path.join(T, 'new', ID + '.png'))

if __name__ == '__main__':
    main()
