# -*- coding: utf-8 -*-
"""아무 파일에서나 PVR 텍스처를 잘라 낱장 .pvr 로 (읽기 전용, 출력 폴더에만 씀). .GZ 는 풀어서.
GBIX 가 바로 앞에 있으면 함께 붙인다. 출력 이름 = <파일>__<PVRT위치 16진>.pvr
  python tools/pvr_carve.py <출력폴더> <파일들…>"""
import sys, os, gzip, struct
GZ_MAGIC = bytes((0x1F, 0x8B))
def carve(path, out):
    d = open(path, 'rb').read()
    if d[:2] == GZ_MAGIC: d = gzip.decompress(d)
    base = (os.path.basename(os.path.dirname(path)) + '_' + os.path.basename(path)).replace('.', '_')  # 장면마다 같은 이름(MPK00) → 폴더 붙임
    n = 0; i = 0
    while True:
        i = d.find(b'PVRT', i)
        if i < 0 or i + 16 > len(d): break
        sz = struct.unpack_from('<I', d, i + 4)[0]; w, h = struct.unpack_from('<HH', d, i + 12)
        if 8 <= w <= 1024 and 8 <= h <= 1024 and i + 8 + sz <= len(d):
            st = i - 16 if i >= 16 and d[i-16:i-12] == b'GBIX' else i
            open(os.path.join(out, '%s__%X.pvr' % (base, i)), 'wb').write(d[st:i + 8 + sz]); n += 1
        i += 8
    return n
if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    print(sum(carve(p, out) for p in sys.argv[2:]))
