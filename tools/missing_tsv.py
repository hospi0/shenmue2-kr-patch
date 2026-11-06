# -*- coding: utf-8 -*-
"""빠진 번역 TSV 만들기(2026-11-06) — 자막(work/text/missing_srf.tsv) + SCNF·메모(work/text/missing.tsv)
  → my files/tsv/sm2_185.tsv ~ (18 KB 단위, 자투리는 앞 묶음에). 열: key · speaker · count · jp · ko
  메모(memo:위치): jp 는 사전 코드·공백 코드를 풀어 쓴 문장. 번역은 코드 없이 한 줄 9칸(18 B) 안에 그대로 쓰면 된다.
  후리가나(RUBI 전용 문자열)·틀 그림 줄은 뺀다.
"""
import os, sys, re, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import missing_text as M
CHUNK = 18 * 1024; START = 185
B = 0x8C010000; DICT = 0x241DC8

def load_dict(d):
    out = []; a = DICT
    while True:
        v = struct.unpack_from('<I', d, a)[0]
        if not B <= v < B + len(d): break
        o = v - B; out.append(d[o:d.index(0, o)].decode('euc_jp', 'replace')); a += 4
    return out

def expand(s, W):
    """해독 루틴 0x8C0D6500 그대로: @ + 5 B 머리, 2바이트 글자 복사, 0n = 전각 공백 n, 나머지 두 숫자 = 사전"""
    out = ''; i = 0; head = ''
    if s[:1] == b'@': head = s[:6].decode('ascii', 'replace'); i = 6
    while i < len(s):
        c = s[i]
        if c >= 0x80:
            out += s[i:i+2].decode('euc_jp', 'replace'); i += 2; continue
        if c == 0x30 and i + 1 < len(s):
            out += '　' * (s[i+1] - 48); i += 2; continue
        if 0x31 <= c <= 0x39 and i + 1 < len(s):
            k = (c - 49) * 10 + s[i+1] - 48
            out += W[k] if k < len(W) else '?'; i += 2; continue
        out += chr(c); i += 1
    return head, out

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    exe = open(os.path.join(ROOT, 'work', 'disc1', '1ST_READ.BIN'), 'rb').read()
    W = load_dict(exe)
    import iso_extract as ie
    from gdi import Disc
    D = Disc(1); ie.D = D
    e = next(x for x in ie.walk() if x[0] == '/MISC/MEMODATA.BIN'); b = D.read(e[1], e[2])
    c = M.memo_chunks(b); mo, ml = c['MEMO']
    ref = {v for v in struct.unpack_from('<%dI' % ((ml - 8) // 4), b, mo + 8) if v != 0xFFFFFFFF}
    rows = []
    for l in open(os.path.join(ROOT, 'work', 'text', 'missing_srf.tsv'), encoding='utf-8'):
        wh, sp, n, jp = l.rstrip('\n').split('\t')
        if jp.strip('　 ') and sp != 'dumy': rows.append(('srfx:' + wh, sp, n, jp))
    for l in open(os.path.join(ROOT, 'work', 'text', 'missing.tsv'), encoding='utf-8').read().split('\n')[1:]:
        q = l.split('\t')
        if len(q) >= 6 and q[0] == 'scnf': rows.append((q[1], q[2], q[3], q[4]))
    seen = set(r[3] for r in rows); rows = list({r[3]: r for r in rows}.values())
    skip = 0
    for o, s in M.memo_strings(b):
        if o not in ref: skip += 1; continue
        h, t = expand(s, W)
        if not re.search(r'[ぁ-ゖァ-ヺ]|[一-鿿]', re.sub('[纐-罍蠡-蠢膣-辯]', '', t)): skip += 1; continue
        rows.append(('memo:%X' % o, '메모 9칸', '1', t))
    print('줄', len(rows), '뺌', skip)
    out = []; cur = ['key\tspeaker\tcount\tjp\tko\n']; size = 0
    for r in rows:
        ln = '%s\t%s\t%s\t%s\t\n' % r
        if size + len(ln.encode('utf-8')) > CHUNK and len(cur) > 1:
            out.append(cur); cur = ['key\tspeaker\tcount\tjp\tko\n']; size = 0
        cur.append(ln); size += len(ln.encode('utf-8'))
    if len(cur) > 1:
        if out and size < CHUNK // 3: out[-1] = out[-1] + cur[1:]
        else: out.append(cur)
    dst = os.path.join(ROOT, 'my files', 'tsv')
    total = 0
    for i, ch in enumerate(out, START):
        open(os.path.join(dst, 'sm2_%03d.tsv' % i), 'w', encoding='utf-8', newline='\n').write(''.join(ch)); total += len(ch) - 1
    assert total == len(rows), (total, len(rows))
    print('묶음 sm2_%03d ~ sm2_%03d · %d줄' % (START, START + len(out) - 1, total))

if __name__ == '__main__':
    main()
