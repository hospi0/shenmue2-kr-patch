# -*- coding: utf-8 -*-
"""MISC/MEMODATA.BIN 다시 쓰기(2026-11-06) — MEMO(줄 → MSTR 위치) · RUBI(줄 → 후리가나 위치) · MSTR(문자열).
  번역(키 memo:<MSTR 위치>)은 사전 코드 없이 풀어 쓴 문장. 한 줄 9칸(18 B) 넘으면 빌드 중단.
  · 해독 루틴 0x8C0D6500: @ + 5 B 머리 복사 / 2바이트 글자 복사 / 0n = 전각 공백 n / 두 숫자 = 사전 → 글자는 전부 2바이트로(반각 금지)
  · 번역이 하나라도 있으면 RUBI 를 전부 -1(후리가나 없음)로, 후리가나 전용 문자열은 버린다.
  · 파일 크기는 원본 그대로(게임 읽기 버퍼 크기 미확인) — 넘치면 빌드 중단.
  python tools/build_memo.py --test   → 번역 없이 원본과 같은지 · 전 줄 시험 글로 크기 검사
"""
import os, sys, re, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import missing_text as M
from encode import encode, normalize
NONE = 0xFFFFFFFF
LINE = 9

def enc_line(ko):
    t = normalize(ko.replace(' ', '　'))
    if len(t.rstrip('　')) > LINE: raise SystemExit('메모 줄 %d칸 > %d칸: %s' % (len(t), LINE, ko))
    out = bytearray(); i = 0
    while i < len(t):                                   # 전각 공백 2칸 이상은 0n 으로(바이트 절약)
        if t[i] == '　':
            j = i
            while j < len(t) and t[j] == '　' and j - i < 9: j += 1
            if j - i >= 2: out += b'0' + str(j - i).encode(); i = j; continue
        out += encode(t[i]); i += 1
    return bytes(out)

def red_head(ko):
    """@ 줄 머리 = 칸별 빨강 표: 두 칸에 숫자 하나(앞 칸 4 + 뒤 칸 1). 원문 44444·41104·01500·45544·55555 로 실측 — 글자 있는 칸이 전부 빨강"""
    t = normalize(ko.replace(' ', '　')).ljust(10, '　')
    return b'@' + bytes(0x30 + (4 if t[2 * k] != '　' else 0) + (1 if t[2 * k + 1] != '　' else 0) for k in range(5))

def build(b, tr):
    """tr = {MSTR 위치: 번역}. 돌려줌 새 파일, 번역 줄 수"""
    c = M.memo_chunks(b); mo, ml = c['MEMO']; ro, rl = c['RUBI']; so, sl = c['MSTR']
    memo = list(struct.unpack_from('<%dI' % ((ml - 8) // 4), b, mo + 8)); rubi = list(struct.unpack_from('<%dI' % ((rl - 8) // 4), b, ro + 8))
    strs = M.memo_strings(b); starts = {o for o, s in strs}
    if not tr: return b, 0
    keep = {v for v in memo if v != NONE}
    bad = [v for v in keep if v not in starts]
    if bad: raise SystemExit('MEMO 값이 문자열 시작이 아님 %s' % bad[:5])
    pool = bytearray(); newoff = {}; seen = {}; n = 0
    for o, s in strs:
        if o not in keep: continue
        if o in tr:
            head = red_head(tr[o]) if s[:1] == b'@' else b''
            s = head + enc_line(tr[o]); n += 1
        if s in seen: newoff[o] = seen[s]; continue
        newoff[o] = seen[s] = len(pool); pool += s + b'\0'
    cap = sl - 8
    if len(pool) > cap: raise SystemExit('MSTR 넘침 %d B > %d B' % (len(pool), cap))
    out = bytearray(b)
    struct.pack_into('<%dI' % len(memo), out, mo + 8, *[newoff[v] if v != NONE else NONE for v in memo])
    struct.pack_into('<%dI' % len(rubi), out, ro + 8, *[NONE] * len(rubi))
    out[so + 8:so + sl] = bytes(pool) + bytes(cap - len(pool))
    return bytes(out), n

def test():
    sys.stdout.reconfigure(encoding='utf-8')
    import iso_extract as ie
    from gdi import Disc
    D = Disc(1); ie.D = D
    e = next(x for x in ie.walk() if x[0] == '/MISC/MEMODATA.BIN'); b = D.read(e[1], e[2])
    print('번역 없음 = 원본', build(b, {})[0] == b)
    keys = [l.split('\t')[0][5:] for f in sorted(os.listdir(os.path.join(ROOT, 'my files', 'tsv'))) if f >= 'sm2_185'
            for l in open(os.path.join(ROOT, 'my files', 'tsv', f), encoding='utf-8') if l.startswith('memo:')]
    tr = {int(k, 16): '가나다라마바사아자' for k in keys}
    nb, n = build(b, tr)
    c = M.memo_chunks(nb); so, sl = c['MSTR']
    print('시험(전 줄 9칸 다름 없는 최악 쪽): 줄', n, '크기', len(nb), len(b), 'MSTR 쓴 양', sl - 8 - (len(nb[so+8:so+sl]) - len(nb[so+8:so+sl].rstrip(b'\0'))), '/', sl - 8)
    ks = [bytes((0xB0 + i // 94, 0xA1 + i % 94)).decode('euc_kr') for i in range(2000)]
    tr2 = {o: '가나다라마바사아' + ks[i % 2000] for i, o in enumerate(tr)}
    nb, n = build(b, tr2)
    print('서로 다른 9칸 전 줄 통과', n)

if __name__ == '__main__':
    test()
