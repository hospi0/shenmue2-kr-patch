# -*- coding: utf-8 -*-
"""쉔무 II 그림 재포장(2026-11-06) — work/tex/new/<id>.png → 원본과 같은 PVR 형식 → 4장 «모든 사본»(gzip·AFS 안까지) 제자리 교체.
  id = 원본 PVR 바이트 sha1 앞 12(tools/tex_dump.py 와 같은 잘라내기). 사본 위치는 work/tex/index.tsv 의 출처로 찾는다.
  이미 빌드된 파일(work/build/common·discN)이 있으면 그 위에 덮음 → ★build_text 다음에 돌릴 것.
  출력 work/build/tex_discN/<경로>, 다시 압축한 파일 목록 work/build/tex_touched_discN.txt, 인코딩 저장 work/build/tex_enc/<id>.pvr
  python tools/tex_pack.py
"""
import os, sys, gzip, glob, hashlib, struct, shutil, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gfx_pack as G, pak
import iso_extract as ie
from gdi import Disc
T = os.path.join(ROOT, 'work', 'tex'); B = os.path.join(ROOT, 'work', 'build')
ENC = os.path.join(B, 'tex_enc')

def carve(d):
    i = 0
    while True:
        i = d.find(b'PVRT', i)
        if i < 0 or i + 16 > len(d): return
        sz = struct.unpack_from('<I', d, i + 4)[0]; w, h = struct.unpack_from('<HH', d, i + 12)
        if 8 <= w <= 1024 and 8 <= h <= 1024 and 16 <= sz and i + 8 + sz <= len(d) + 64:
            st = i - 16 if i >= 16 and d[i - 16:i - 12] == b'GBIX' else i
            yield st, min(len(d), i + 8 + sz)
        i += 8

class Packer:
    def __init__(self, ids):
        self.ids = ids; self.cache = {}; self.bad = {}; self.hit = 0; self.found = set()
    def enc(self, k, pvr):
        if k in self.cache: return self.cache[k]
        p = os.path.join(ENC, k + '.pvr')
        src = os.path.join(T, 'new', k + '.png')
        if os.path.exists(p) and os.path.getmtime(p) >= os.path.getmtime(src):   # PNG 가 더 새로우면 다시 인코딩(옛 캐시로 수정이 빠졌던 사고)
            e = open(p, 'rb').read()
        else:
            px, df, w, h = G.pvr_info(pvr)
            e = G.encode(os.path.join(T, 'new', k + '.png'), px, df, G.gbix_of(pvr))
            open(p, 'wb').write(e)
        self.cache[k] = e; return e
    def flat(self, d):
        """d 안 PVR 바꾸기. 돌려줌 (bytes, 바꾼 수)"""
        b = None; n = 0
        for st, en in list(carve(d)):
            pvr = d[st:en]; k = hashlib.sha1(pvr).hexdigest()[:12]
            if k not in self.ids or k in self.bad: continue
            try: e = self.enc(k, pvr)
            except Exception as ex:
                self.bad[k] = repr(ex)[:80]; print('! 인코딩 실패', k, ex, flush=True); continue
            if len(e) != en - st:
                self.bad[k] = '크기 %d ≠ %d' % (len(e), en - st); print('! 크기 다름', k, len(e), en - st, flush=True); continue
            if b is None: b = bytearray(d)
            b[st:en] = e; n += 1; self.found.add(k)
        return (bytes(b) if b is not None else d), n
    def proc(self, d, depth=0):
        """gzip·AFS 안까지. 돌려줌 (bytes, 바꾼 수)"""
        if depth > 4: return d, 0
        if d[:2] == b'\x1f\x8b':
            try: x = gzip.decompress(d)
            except Exception: return d, 0
            y, n = self.proc(x, depth + 1)
            return (pak.regzip(d, y), n) if n else (d, 0)
        d2, n = self.flat(d)
        if d2[:4] == b'AFS\0':
            b = bytearray(d2); cnt = struct.unpack_from('<I', b, 4)[0]
            offs = [struct.unpack_from('<II', b, 8 + 8 * k) for k in range(min(cnt, 100000)) if 8 + 8 * k + 8 <= len(b)]
            for k, (o, s) in enumerate(offs):
                if not (0 < o < len(b) and 0 < s <= len(b) - o): continue
                sub = bytes(b[o:o + s])
                if sub[:2] != b'\x1f\x8b' and sub[:4] != b'AFS\0': continue
                y, m = self.proc(sub, depth + 1)
                if not m: continue
                room = ((offs[k + 1][0] if k + 1 < len(offs) else len(b)) - o)
                if len(y) > room: print('! AFS 안 항목 넘침', k, len(y), room, flush=True); continue
                b[o:o + len(y)] = y; b[o + len(y):o + room] = bytes(room - len(y)); struct.pack_into('<I', b, 8 + 8 * k + 4, len(y)); n += m
            d2 = bytes(b)
        return d2, n

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(ENC, exist_ok=True)
    ids = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(T, 'new', '*.png'))}
    print('새 그림', len(ids))
    where = collections.defaultdict(set)
    for l in open(os.path.join(T, 'index.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = l.split('\t')
        if len(c) < 8 or c[0] not in ids: continue
        for w in c[7].split(' '):
            if ':' not in w: continue
            n, r = w.split(':', 1); where[int(n)].add(r.split('@')[0].split('#')[0])
    P = Packer(ids); tot = 0
    for n in (1, 2, 3, 4):
        dst = os.path.join(B, 'tex_disc%d' % n)
        if os.path.isdir(dst): shutil.rmtree(dst)
        D = Disc(n); ie.D = D
        E = {e[0]: e for e in ie.walk() if not e[3] & 2}
        touched = []
        for f in sorted(where[n]):
            rel = f.lstrip('/')
            src = next((p for p in (os.path.join(B, 'disc%d' % n, rel), os.path.join(B, 'common', rel)) if os.path.exists(p)), None)
            raw = open(src, 'rb').read() if src else D.read(E[f][1], E[f][2])
            out, k = P.proc(raw)
            if not k: continue
            q = os.path.join(dst, rel); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(out)
            if raw[:2] == b'\x1f\x8b' or raw[:4] == b'AFS\0': touched.append(f)
            tot += k
        open(os.path.join(B, 'tex_touched_disc%d.txt' % n), 'w', encoding='utf-8').write('\n'.join(touched) + '\n')
        print('장 %d: 파일 %d · 누계 교체 %d · 인코딩 %d' % (n, len(where[n]), tot, len(P.cache)), flush=True)
    print('교체 %d곳 · 인코딩 %d장 · 실패 %d' % (tot, len(P.cache), len(P.bad)))
    for k, v in list(P.bad.items())[:30]: print('  실패', k, v)
    miss = ids - P.found - set(P.bad)
    print('디스크에서 못 찾은 id', len(miss), sorted(miss)[:20])
    print('TEX_PACK_OK')

if __name__ == '__main__':
    main()
