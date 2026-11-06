# -*- coding: utf-8 -*-
"""그림 재포장 — work/gfx/new/*.png(한글) → 원본과 같은 PVR 형식 → 게임이 읽는 «모든 사본» 컨테이너에 제자리로.
사본: SPRITE/*.SPR · SPRITE/*.GZ(gzip SPR) · TITLE/*.SPR · MODEL/ITEM/*.SPR · MISC/TEXTURES.PKS(gzip PAKS 안 COMICON=SPR)
SPR = TEXN 청크('TEXN'+u32 크기+8B 이름+GBIX…PVRT…). 텍스처 이름 = <SPR 이름>__<순번 2자리>_<TEXN 이름>(gfx 원본 PNG 이름과 같음)."""
import os, sys, struct, glob, gzip
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pak
D1 = os.path.join(ROOT, 'work', 'disc1')
PXF = {0: '1555', 1: '565', 2: '4444', 3: 'yuv422', 4: 'bump', 5: '555', 6: 'yuv420', 7: '8888'}

def texn_chunks(spr):
    """[(순번, 이름, PVR 시작, PVR 끝)] — PVR = GBIX…PVRT…끝"""
    out = []; p = 0; n = 0
    while p + 8 <= len(spr):
        tag = spr[p:p+4]; sz = struct.unpack_from('<I', spr, p + 4)[0]
        if sz < 8 or p + sz > len(spr): break
        if tag == b'TEXN':
            raw = spr[p+8:p+16].split(b'\0')[0]
            nm = ''.join(chr(c) if (48 <= c < 58 or 65 <= c < 91 or 97 <= c < 123) else '_' for c in raw) or str(n)
            out.append((n, nm, p + 16, p + sz)); n += 1
        p += sz
    return out

def containers():
    """[(디스크 경로, 종류, 베이스 이름)] 종류: spr / gz / pks"""
    out = []
    for pat, kind in (('SPRITE/*.SPR', 'spr'), ('SPRITE/*.GZ', 'gz'), ('TITLE/*.SPR', 'spr'), ('MODEL/ITEM/*.SPR', 'spr')):
        for f in sorted(glob.glob(os.path.join(D1, pat))):
            out.append(('/' + os.path.relpath(f, D1).replace(os.sep, '/'), kind, os.path.splitext(os.path.basename(f))[0]))
    out.append(('/MISC/TEXTURES.PKS', 'pks', 'COMICON'))
    return out

def spr_of(path, kind):
    raw = open(os.path.join(D1, path.lstrip('/')), 'rb').read()
    if kind == 'gz': return raw, gzip.decompress(raw)
    if kind == 'pks':
        _, d = pak.load(os.path.join(D1, path.lstrip('/'))); o, s = pak.entries(d)['COMICON']; return raw, d[o:o+s]
    return raw, raw

def pvr_info(pvr):
    i = pvr.find(b'PVRT'); px, df = pvr[i+8], pvr[i+9]; w, h = struct.unpack_from('<HH', pvr, i + 12)
    return px, df, w, h

if __name__ == '__main__' and (len(sys.argv) < 2 or sys.argv[1] != 'pack'):
    sys.stdout.reconfigure(encoding='utf-8')
    new = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(ROOT, 'work', 'gfx', 'new', '*.png'))}
    seen = {}
    for path, kind, base in containers():
        _, spr = spr_of(path, kind)
        for n, nm, a, b in texn_chunks(spr):
            key = '%s__%02d_%s' % (base, n, nm)
            if key in new:
                px, df, w, h = pvr_info(spr[a:b]); seen.setdefault(key, []).append((path, PXF.get(px, px), hex(df), w, h))
    import collections
    c = collections.Counter((v[0][1], v[0][2]) for v in seen.values())
    print('바꿀 텍스처', len(seen), '/ 새 PNG', len(new), '· 형식', dict(c))
    print('사본 수 분포', collections.Counter(len(v) for v in seen.values()))
    print('못 찾음', sorted(new - set(seen))[:20])


TEXF = {0x1: 'tw', 0x3: 'vq', 0x9: 're', 0xD: 'twre', 0x5: 'pal4', 0x7: 'pal8', 0x10: 'svq', 0x11: 'svq'}

def encode(png_path, px, df, gbix, flip=False):   # ★PyPVR 인코딩은 -flip 없이(디코딩 -flip PNG 와 짝 — 실측 2026-11-04)
    """PyPVR 로 PNG → PVR(GBIX 포함). 경로에 «-» 있으면 PyPVR 이 실패 → %TEMP% 의 하이픈 없는 폴더에서."""
    import tempfile, shutil, subprocess
    td = tempfile.mkdtemp(prefix='shmenc')
    try:
        src = os.path.join(td, 'a.png')
        from PIL import Image, ImageOps
        im = Image.open(png_path)
        if not flip: im = ImageOps.flip(im)      # ★우리 PNG 는 -flip 으로 푼 «똑바로 선» 그림 → PyPVR 인코딩 전에 직접 뒤집음(인코딩 -flip 은 무시됨, 실측)
        im.save(src)
        args = [sys.executable, r'C:\claude\utils\dreamcast\PyPVR\pypvr.py', src, '-' + PXF[px], '-' + TEXF[df], '-o', td, '-silent', '-nopvp']
        if gbix is not None: args += ['-gi', str(gbix), '-gitrim']        # 원본 = 짧은 GBIX(4 B)
        if TEXF[df] == 'vq': args += ['-vqa1']                             # faiss 없음 → VQ 알고리즘 1
        r = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
        outs = glob.glob(os.path.join(td, '*.pvr'))
        if not outs: raise RuntimeError('PyPVR 실패: ' + (r.stdout + r.stderr)[-400:])
        return open(outs[0], 'rb').read()
    finally:
        shutil.rmtree(td, ignore_errors=True)

def gbix_of(pvr):
    return struct.unpack_from('<I', pvr, 8)[0] if pvr[:4] == b'GBIX' else None


OUT = os.path.join(ROOT, 'work', 'build', 'gfx_common')

def pack(only=None, log=print):
    """새 PNG 있는 텍스처를 모든 사본 컨테이너에 제자리로. 같은 텍스처는 한 번만 인코딩(캐시)."""
    import shutil
    newdir = os.path.join(ROOT, 'work', 'gfx', 'new')
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    cache = {}; done = 0
    for path, kind, base in containers():
        raw, spr = spr_of(path, kind); spr2 = bytearray(spr); changed = 0
        for n, nm, a, b in texn_chunks(spr):
            key = '%s__%02d_%s' % (base, n, nm)
            png = os.path.join(newdir, key + '.png')
            if not os.path.exists(png) or (only and key not in only): continue
            pvr = spr[a:b]; px, df, w, h = pvr_info(pvr)
            if key not in cache:
                cache[key] = encode(png, px, df, gbix_of(pvr))
            e = cache[key]
            if len(e) != len(pvr): raise SystemExit('%s 크기 %d ≠ 원본 %d' % (key, len(e), len(pvr)))
            spr2[a:b] = e; changed += 1
        if not changed: continue
        spr2 = bytes(spr2)
        if kind == 'gz': out = pak.regzip(raw, spr2)
        elif kind == 'pks':
            _, d = pak.load(os.path.join(D1, path.lstrip('/')))
            out = pak.regzip(raw, pak.replace_same_size(d, {'COMICON': spr2}))
        else: out = spr2
        dst = os.path.join(OUT, path.lstrip('/')); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(out); done += changed
        log('%-26s %s 텍스처 %d개 · %d → %d B' % (path, kind, changed, len(raw), len(out)))
    log('넣은 텍스처(사본 포함) %d · 인코딩 %d' % (done, len(cache)))

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'pack':
    sys.stdout.reconfigure(encoding='utf-8'); pack()
