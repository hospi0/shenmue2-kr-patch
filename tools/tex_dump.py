# -*- coding: utf-8 -*-
"""쉔무 II 그림·텍스처 전수 추출(읽기 전용, 2026-11-05 — 쉔무 1 tools/scene_tex.py 를 옮김).
4장 디스크에서 파일을 바로 읽어(풀어 둔 트리 불필요) 모든 PVRT 를 잘라(gzip·AFS 안까지) 같은 바이트는 하나로 묶고 PNG 로.
  → work/tex/png/<sha1 앞 12>.png
  → work/tex/index.tsv   (id · 폭 · 높이 · 픽셀형식 · 텍스처형식 · 사본 수 · 분류(맨 위 폴더) · 출처 전부)
  → work/tex/sheets/<분류>_NNN.png (훑어보기 표: 칸마다 id·크기)
  건너뜀: */STREAM/*·*/MOVIE/* (음성·동영상), 64 MB 넘는 파일.
  python tools/tex_dump.py
"""
import os, sys, gzip, struct, hashlib, collections
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, r'C:\claude\utils\dreamcast\PyPVR')
import iso_extract
from gdi import Disc
from pypvr import Pypvr
OUT = os.path.join(ROOT, 'work', 'tex')

def blobs(d, where, depth=0):
    if depth > 4: return
    if d[:2] == b'\x1f\x8b':
        try: d = gzip.decompress(d)
        except Exception: return
    yield d, where
    if d[:4] == b'AFS\0':
        n = struct.unpack_from('<I', d, 4)[0]
        for k in range(min(n, 100000)):
            if 8 + 8 * k + 8 > len(d): break
            o, s = struct.unpack_from('<II', d, 8 + 8 * k)
            if 0 < o < len(d) and 0 < s <= len(d) - o:
                sub = d[o:o + s]
                if sub[:2] == b'\x1f\x8b' or sub[:4] == b'AFS\0':
                    yield from blobs(sub, '%s#%d' % (where, k), depth + 1)

def carve(d):
    i = 0
    while True:
        i = d.find(b'PVRT', i)
        if i < 0 or i + 16 > len(d): return
        sz = struct.unpack_from('<I', d, i + 4)[0]; w, h = struct.unpack_from('<HH', d, i + 12)
        if 8 <= w <= 1024 and 8 <= h <= 1024 and 16 <= sz and i + 8 + sz <= len(d) + 64:
            st = i - 16 if i >= 16 and d[i - 16:i - 12] == b'GBIX' else i
            yield i, d[st:min(len(d), i + 8 + sz)], w, h, d[i + 8], d[i + 9]
        i += 8

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(os.path.join(OUT, 'png'), exist_ok=True); os.makedirs(os.path.join(OUT, 'sheets'), exist_ok=True)
    seen = collections.OrderedDict(); bad = 0
    for n in (1, 2, 3, 4):
        D = Disc(n); iso_extract.D = D
        ents = [e for e in iso_extract.walk() if not (e[3] & 2)]
        print('장 %d 파일 %d' % (n, len(ents)), flush=True)
        for fi, (full, lba, size, fl) in enumerate(ents):
            U = full.upper()
            if '/STREAM/' in U or '/MOVIE/' in U or size > 64 << 20: continue
            data = D.read(lba, size)
            if b'PVRT' not in data and data[:2] != b'\x1f\x8b': continue
            top = full.strip('/').split('/')[0] if '/' in full.strip('/') else 'ROOT'
            for d, where in blobs(data, '%d:%s' % (n, full)):
                for off, pvr, w, h, px, tf in carve(d):
                    k = hashlib.sha1(pvr).hexdigest()[:12]
                    if k in seen: seen[k][5].append('%s@%X' % (where, off)); continue
                    p = os.path.join(OUT, 'png', k + '.png')
                    if not os.path.exists(p):
                        try: Pypvr.Decode('-buffer -flip -silent -nolog', buff_pvr=pvr).get_image_buffer().save(p)
                        except Exception: bad += 1; continue
                    seen[k] = [w, h, px, tf, top, ['%s@%X' % (where, off)]]
            if fi % 400 == 0: print('  %d/%d 텍스처 %d' % (fi, len(ents), len(seen)), flush=True)
    with open(os.path.join(OUT, 'index.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('id\tw\th\tpx\ttf\tcopies\tgroup\tsources\n')
        for k, (ww, hh, px, tf, top, src) in seen.items():
            w.write('%s\t%d\t%d\t%d\t%d\t%d\t%s\t%s\n' % (k, ww, hh, px, tf, len(src), top, ' '.join(src)))
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 12)
    groups = collections.OrderedDict()
    for k, v in seen.items(): groups.setdefault(v[4], []).append(k)
    C, R, S = 8, 5, 200; nsheet = 0
    for g, ids in groups.items():
        for pg in range(0, len(ids), C * R):
            sh = Image.new('RGB', (C * S, R * (S + 16)), (40, 40, 48)); dr = ImageDraw.Draw(sh)
            for j, k in enumerate(ids[pg:pg + C * R]):
                try: im = Image.open(os.path.join(OUT, 'png', k + '.png')).convert('RGBA')
                except Exception: continue
                im.thumbnail((S - 6, S - 6))
                bg = Image.new('RGBA', im.size, (128, 128, 128, 255)); bg.alpha_composite(im)
                x, y = (j % C) * S, (j // C) * (S + 16)
                sh.paste(bg.convert('RGB'), (x + 3, y + 3)); dr.text((x + 3, y + S), '%s %dx%d' % (k, seen[k][0], seen[k][1]), font=font, fill=(255, 220, 80))
            sh.save(os.path.join(OUT, 'sheets', '%s_%03d.png' % (g, pg // (C * R) + 1))); nsheet += 1
    print('고유 텍스처 %d · 풀기 실패 %d · 분류 %s · 표 %d장 → %s' % (len(seen), bad, {g: len(v) for g, v in groups.items()}, nsheet, OUT))

if __name__ == '__main__':
    main()
