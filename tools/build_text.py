# -*- coding: utf-8 -*-
"""쉔무 II 번역 → 빌드 재료(2026-11-06). 1편 build_text 를 II 형식(SRF 꼬리표·IDX·장마다 다른 HUMANS·트랙)에 맞춤.
  python tools/build_text.py            (번역 = work/text/ko/sm2_*.tsv + work/text/ko_extra/*.tsv)
  출력 work/build/common(모든 장 공통: 글꼴 COLD.BIN·FON, SCNF, 1ST_READ) · work/build/discN(AFS·IDX·HUMANS)
규칙: 자막 19칸×2줄, 넘치면 낱말로 다시 접고 work/build/text_report.tsv 에 보고. 같은 원문 = 같은 번역. 번역 없으면 원문 그대로.
"""
import os, sys, glob, re, struct, shutil, subprocess, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import iso_extract as ie, srf2w, pks, pak, scnf_text
from afs import build_afs
from gdi import Disc
from encode import encode, normalize
W = lambda *p: os.path.join(ROOT, 'work', *p)
B = W('build')
WIDTH, MAXLINES = 19, 2

def load_tr():
    tr = {}
    for p in sorted(glob.glob(W('text', 'ko', 'sm2_*.tsv'))) + sorted(glob.glob(W('text', 'ko_extra', '*.tsv'))):
        for i, ln in enumerate(open(p, encoding='utf-8')):
            c = ln.rstrip('\n').split('\t')
            if c[0] == 'key' or len(c) < 5 or not c[4].strip(): continue
            g = 'exe' if c[0].startswith('exe:') else 'memo' if c[0].startswith('memo:') else 'talk'
            tr[(g, c[3])] = (c[0], c[4])
    return tr

def wrap_words(parts):
    words = ' '.join(p.strip() for p in parts).split(' ')
    lines = ['']
    for w in words:
        cand = (lines[-1] + ' ' + w) if lines[-1] else w
        if len(cand) <= WIDTH: lines[-1] = cand
        elif not lines[-1]: lines[-1] = w
        else: lines.append(w)
    return lines

def wrap(ko):
    ko = normalize(ko); parts = ko.split('＆')
    if all(len(p) <= WIDTH for p in parts) and len(parts) <= MAXLINES: return parts
    if len(parts) > MAXLINES and all(len(p) <= WIDTH for p in parts):
        alt = wrap_words(parts)
        return alt if len(alt) <= MAXLINES else parts
    return wrap_words(parts)

def ok_enc(c):
    try: encode(c); return True
    except Exception: return False

def afs_table(d):
    n = struct.unpack_from('<I', d, 4)[0]
    return [struct.unpack_from('<II', d, 8 + 8 * i) for i in range(n)]

def prepare_font(tr):
    mine = set(''.join(v[1] for v in tr.values())); used = set(mine)
    for l in open(W('text', 'lines.tsv'), encoding='utf-8'):
        c = l.split('\t')
        if len(c) >= 4: used |= set(c[3])
    for l in open(W('text', 'missing.tsv'), encoding='utf-8'):     # 메모 틀 그림 칸·원문 글자는 덮지 않음
        c = l.split('\t')
        if len(c) >= 5: used |= set(c[4])
    os.makedirs(W('font'), exist_ok=True)
    av = W('font', 'avoid_chars.txt'); open(av, 'w', encoding='utf-8').write(''.join(sorted(used)))
    subprocess.run([sys.executable, os.path.join(HERE, 'build_font.py'), '--extra', ''.join(sorted(mine)), '--avoid', av], check=True)
    import encode as _e; _e._EX = None

def fonts(cold):
    """게임이 쓰는 글꼴 = MISC/COLD.BIN 안 DC_KANJI·RYOU. 원본과 다른 칸만 원본 묶음 칸 위에 덮는다(1편 build_test.overlay 와 같은 뜻)."""
    dst = os.path.join(B, 'common', 'MISC'); os.makedirs(dst, exist_ok=True)
    ents = pak.entries(cold); repl = {}
    for f in ('DC_KANJI', 'RYOU'):
        built = open(W('font', f + '.FON'), 'rb').read(); shutil.copyfile(W('font', f + '.FON'), os.path.join(dst, f + '.FON'))
        o, s = ents[f]; assert s == len(built), (f, s, len(built))
        import build_font as BF                                     # 게임이 기술 설명 끝에 찍는 。(1구 3칸) → 한국식 . (1구 5칸 그림)
        built = bytearray(built); built[BF.slot(1, 3) * BF.GB:(BF.slot(1, 3) + 1) * BF.GB] = built[BF.slot(1, 5) * BF.GB:(BF.slot(1, 5) + 1) * BF.GB]; built = bytes(built)
        repl[f] = built
    import build_font
    o, s_ = ents['DC_KANA']; repl['DC_KANA'] = build_font.kana_font(cold[o:o + s_])
    return pak.replace_same_size(cold, repl)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tr = load_tr()
    print('번역 원문 %d' % len(tr))
    for d in ('common', 'disc1', 'disc2', 'disc3', 'disc4'):
        if os.path.isdir(os.path.join(B, d)): shutil.rmtree(os.path.join(B, d))
    os.makedirs(os.path.join(B, 'common', 'MISC'), exist_ok=True)
    prepare_font(tr)
    report = []; seen_over = set()
    def lines_of(jp, where):
        v = tr.get(('talk', jp))
        if not v: return None
        L = wrap(v[1])
        if (len(L) > MAXLINES or any(len(x) > WIDTH for x in L)) and jp not in seen_over:
            seen_over.add(jp); report.append('넘침\t%s\t%d줄\t%s' % (where, len(L), '＆'.join(L)))
        return L
    D = Disc(1); ie.D = D
    E = {e[0]: e for e in ie.walk() if not e[3] & 2}
    rd = lambda f: D.read(E[f][1], E[f][2])
    # 1) 글꼴 + SCNF(COLD.BIN 안 SYSTALK · FREETALK 등)
    cold = fonts(rd('/MISC/COLD.BIN'))
    SPK = {'涼': '료'}; tight = [0]     # SCNF 크기 고정 — 넘치면 화자(화면에 안 나옴)를 첫 글자만
    def scnf_tr(idk, jt):
        spk, body = (jt.split('「', 1) if '「' in jt else ('', jt))
        if spk and body.endswith('」'): body = body[:-1]
        L = lines_of(body.replace('\n', '＆'), idk) or lines_of(jt.replace('\n', '＆'), idk)
        if L is None: return None
        sp = SPK.get(spk, spk); sp = ''.join(c for c in sp if c != '\ufffd' and ok_enc(c))
        if tight[0]: sp = sp[:1] if tight[0] == 1 else ''
        txt = '\n'.join(L)
        if spk: txt = sp + '「' + txt + '」'
        return b'\n'.join(encode(x) for x in txt.split('\n'))
    nsc = 0; miss = []
    def patch_fit(data, name):
        # SCNF 크기 고정 — 넘치면 화자(화면에 안 나옴)를 첫 글자만 → 그래도 넘치면 비움
        for lv in (0, 1, 2):
            tight[0] = lv
            try:
                r = scnf_text.patch(data, scnf_tr); tight[0] = 0
                if lv: print('  %s: 화자 줄임 단계 %d' % (name, lv))
                return r
            except SystemExit as x:
                if lv == 2: raise
    nd, k, seen = patch_fit(cold, 'COLD'); nsc += k
    miss += [('COLD', i, t) for i, t in seen if scnf_tr(i, t) is None]
    open(os.path.join(B, 'common', 'MISC', 'COLD.BIN'), 'wb').write(nd)
    for fn in ('FREETALK', 'FREETLK1', 'FREETLK2', 'FREETLK3', 'FREETLK4', 'SYSTALK'):
        nd, k, seen = patch_fit(rd('/MISC/%s.BIN' % fn), fn)
        nsc += k
        miss += [(fn, i, t) for i, t in seen if scnf_tr(i, t) is None]
        open(os.path.join(B, 'common', 'MISC', fn + '.BIN'), 'wb').write(nd)
    print('SCNF 번역 %d줄 · 번역 없음 %d' % (nsc, len(miss)))
    import build_memo
    mt = {int(v[0][5:], 16): v[1] for k, v in tr.items() if k[0] == 'memo'}
    if mt:
        nb, k = build_memo.build(rd('/MISC/MEMODATA.BIN'), mt); open(os.path.join(B, 'common', 'MISC', 'MEMODATA.BIN'), 'wb').write(nb); print('메모 %d줄' % k)
    shutil.copyfile(W('tex', '재사용', 'RESUME.DAT'), os.path.join(B, 'common', 'MISC', 'RESUME.DAT'))   # 원본 1편과 같은 파일 → 1편 빌드 그대로
    # 2) 자막(SRF)·IDX · NPC(PKS) 장별
    nsrf = npks = 0; nomatch = collections.Counter(); bad_idx = 0
    for n in (1, 2, 3, 4):
        D = Disc(n); ie.D = D
        E = {e[0]: e for e in ie.walk() if not e[3] & 2}
        for f, e in sorted(E.items()):
            if not ('/STREAM/' in f and f.endswith('.AFS')): continue
            d = D.read(e[1], e[2])
            if d[:4] != b'AFS\0': continue
            ents = afs_table(d); files = []; remaps = {}; changed = False
            names = [('%04d' % i) for i in range(len(ents))]
            for i, (o, s) in enumerate(ents):
                b = d[o:o+s]
                if b[:4] == b'CHID':
                    new = {}
                    for k, r in enumerate(srf2w.records(b)):
                        t = srf2w.text_of(b, r)
                        if t is None or not t: continue
                        jp = t.decode('euc_jis_2004', 'replace')
                        L = lines_of(jp, '%d:%s#%d' % (n, os.path.basename(f), k))
                        if L is None: nomatch['srf'] += 1; continue
                        new[k] = encode('＆'.join(L)); nsrf += 1
                    b, m = srf2w.rebuild(b, new); remaps[i] = m; changed = changed or bool(new)
                files.append((names[i], b))
            if not changed: continue
            dst = os.path.join(B, 'disc%d' % n, f.lstrip('/')); os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(build_afs(d, files))
            ix = f[:-4] + '.IDX'
            if ix in E:
                x = D.read(E[ix][1], E[ix][2])
                y, ms = srf2w.rebuild_idx(x, remaps)
                bad_idx += ms
                open(dst[:-4] + '.IDX', 'wb').write(y)
        # NPC
        f = '/SCENE/0%d/NPC/HUMANS.AFS' % n
        d = D.read(E[f][1], E[f][2]); ents = afs_table(d); files = []
        for i, (o, s) in enumerate(ents):
            b = d[o:o+s]
            if b[:4] == b'PAKS' and pks._scnf_span(b)[2] is not None:
                newt = {}
                for idk, t in pks.strings(b):
                    jt = t.decode('euc_jis_2004', 'replace').replace('\n', '＆')
                    spk, body = (jt.split('「', 1) if '「' in jt else ('', jt))
                    if spk and body.endswith('」'): body = body[:-1]
                    L = lines_of(body, idk)
                    if L is None: nomatch['pks'] += 1; continue
                    body_b = b'\n'.join(encode(x) for x in L)
                    q = t.find('「'.encode('euc_jp'))               # 화자 바이트는 원본 그대로(① 같은 글자, 화면에 안 나옴)
                    newt[idk] = (t[:q + 2] + body_b + '」'.encode('euc_jp')) if spk and q >= 0 else body_b; npks += 1
                if newt: b = pks.rebuild(b, newt)
            files.append(('%04d' % i, b))
        dst = os.path.join(B, 'disc%d' % n, f.lstrip('/')); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(build_afs(d, files))
        print('장 %d 끝: SRF 누계 %d · PKS 누계 %d' % (n, nsrf, npks), flush=True)
    with open(os.path.join(B, 'text_report.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('kind\tkey\tinfo\ttext\n' + ''.join(r + '\n' for r in report))
        for x in miss: w.write('번역없음\t%s\t%s\t%s\n' % (x[0], x[1], x[2].replace('\n', '＆')))
    print('SRF %d · PKS %d · 번역 없음 %s · 넘침 %d · IDX 못 맞춘 항목 %d' % (nsrf, npks, dict(nomatch), len(report), bad_idx))
    print('BUILD_TEXT_OK')

if __name__ == '__main__':
    main()
