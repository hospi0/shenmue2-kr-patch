# -*- coding: utf-8 -*-
"""스테이트 VRAM ↔ 디스크 PVR 텍스처 대조 — «이 화면에 올라간 텍스처»를 찾는다(읽기 전용).

flycast 스테이트(RZIP) 해제 → RAM 위치 = 1ST_READ 바이트로 실측(파일 0 = RAM 0x10000) → VRAM = RAM 바로 앞 8 MB.
텍스처 = 디스크 모든 파일(gzip 이면 풀어서 — PKF 74개 등) 안 'PVRT' 청크. 몸통에서 서로 다른 바이트가 많은 32 B 표본 2개가 VRAM 에 있으면 «올라감».

  python tools/vram_scan.py            → work/vram/hits.tsv (상태, 파일, PVRT 위치, 크기, 형식)
"""
import os, sys, glob, gzip, struct, collections
GZ_MAGIC = bytes((0x1F, 0x8B))
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from rzip import unrzip

def textures():
    out = []
    for dp, dn, fn in os.walk(os.path.join(ROOT, 'work', 'disc1')):
        for f in fn:
            if f.lower().endswith(('.str', '.snd')): continue
            p = os.path.join(dp, f)
            d = open(p, 'rb').read()
            if d[:2] == GZ_MAGIC:           # .GZ 뿐 아니라 PKF·PKS 도 gzip 인 것이 많다(각 77개)
                try: d = gzip.decompress(d)
                except Exception: continue
            i = 0
            while True:
                i = d.find(b'PVRT', i)
                if i < 0 or i + 16 > len(d): break
                sz = struct.unpack_from('<I', d, i + 4)[0]
                fmt = struct.unpack_from('<I', d, i + 8)[0]
                w, h = struct.unpack_from('<HH', d, i + 12)
                body = d[i + 16:i + 8 + sz]
                if 8 <= w <= 1024 and 8 <= h <= 1024 and len(body) >= 64:
                    samples = []
                    for off in range(0, len(body) - 32, max(32, len(body) // 16)):
                        s = body[off:off + 32]
                        if len(set(s)) >= 20: samples.append(s)
                        if len(samples) == 2: break
                    if samples: out.append((os.path.relpath(p, os.path.join(ROOT, 'work', 'disc1')), i, w, h, fmt, samples))
                i += 8
    return out

def vram_of(state_path, exe):
    st = unrzip(open(state_path, 'rb').read())
    c = collections.Counter()
    for off in range(0x10000, len(exe) - 64, 0x10000):
        s = exe[off:off + 32]
        if len(set(s)) < 12: continue
        p = st.find(s)
        if p >= 0: c[p - off] += 1
    base = c.most_common(1)[0][0] - 0x10000          # RAM 0x8C000000 의 스테이트 위치
    return st[base - 0x800000:base]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    exe = open(os.path.join(ROOT, 'work', 'disc1', '1ST_READ.BIN'), 'rb').read()
    tex = textures(); print('텍스처', len(tex))
    out = os.path.join(ROOT, 'work', 'vram'); os.makedirs(out, exist_ok=True)
    rows = []
    for sp in sorted(glob.glob(os.path.join(ROOT, 'work', 'state_20261103', '*.state'))):
        v = vram_of(sp, exe); nm = os.path.basename(sp)[:-6]; n = 0
        for f, i, w, h, fmt, smp in tex:
            if all(s in v for s in smp):
                rows.append('%s\t%s\t%X\t%dx%d\t%08X\n' % (nm, f, i, w, h, fmt)); n += 1
        print(nm, n)
    open(os.path.join(out, 'hits.tsv'), 'w', encoding='utf-8', newline='\n').write(''.join(rows))

if __name__ == '__main__':
    main()
