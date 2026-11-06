# -*- coding: utf-8 -*-
"""쉔무 II SRF·IDX 다시 쓰기(2026-11-06).
SRF = 꼬리표 덩어리 CHID·[STDL]·CLIP…·ENDC. 자막은 STDL(u32 len 은 머리 8 B 포함, 본문 + NUL 1개 이상, 4 B 정렬).
IDX = 'IDXA'(u32 0x14, u16 파일 수, u16 음성 수, …) + 'TABL'(u32 len) + 항목들. 항목에 «SRF 안 레코드 위치»가 들어 있어 자막 길이가 바뀌면 고쳐야 한다.
  항목 20 B: 이름 8 · u32 0 · u16 AFS 번호 · u16 SRF 번호 · u32 레코드 바이트 위치 (0005 등)
  항목 12 B: 이름 4 · u32 0 · u16 AFS 번호 · u16 레코드 위치÷4
"""
import struct

def records(b):
    """[(시작, 끝, STDL 본문 시작, STDL 끝)] — 레코드 = CHID 부터 ENDC 까지. STDL 없으면 None."""
    out = []; i = 0; cur = None
    while i + 8 <= len(b):
        tag = b[i:i+4]; ln = struct.unpack_from('<I', b, i + 4)[0]
        if tag == b'CHID':
            cur = [i, None, None, None]
        elif tag == b'STDL' and cur is not None:
            cur[2], cur[3] = i, i + ln
        elif tag == b'ENDC':
            if cur is not None:
                cur[1] = i + 8; out.append(tuple(cur)); cur = None
            i += 8; continue
        elif not tag.strip(b'\0'):
            i += 4; continue
        if ln < 8: break
        i += ln
    return out

def text_of(b, r):
    if r[2] is None: return None
    return b[r[2]+8:r[3]].rstrip(b'\0')

def stdl(t):
    n = len(t) + 1; n += (-n) % 4
    return b'STDL' + struct.pack('<I', 8 + n) + t + b'\0' * (n - len(t))

def rebuild(b, new):
    """new = {레코드 번호: 자막 bytes}. 돌려줌 (새 SRF, {옛 레코드 위치: 새 위치})."""
    # ★레코드는 2,048 B 섹터 경계를 넘으면 안 된다(원본 32,420개 중 0개) — 게임이 섹터 단위로 읽어 경계 뒤 글자가 낡은 버퍼로 찍힌다(돈을0005).
    #   원본 0 빈틈은 버리고 경계 넘는 레코드 앞에만 0 을 채운다. SRF 시작은 AFS 안 2,048 B 정렬(341개 전부 확인).
    rs = records(b); out = bytearray(); remap = {}; p = 0
    for k, r in enumerate(rs):
        gap = b[p:r[0]]
        if gap.strip(b'\0'): out += gap
        rec = b[r[0]:r[2]] + stdl(new[k]) + b[r[3]:r[1]] if k in new and r[2] is not None else b[r[0]:r[1]]
        assert len(rec) <= 2048, len(rec)
        if len(out) // 2048 != (len(out) + len(rec) - 1) // 2048: out += bytes(-len(out) % 2048)
        remap[r[0]] = len(out); out += rec
        p = r[1]
    out += b[p:]
    remap[len(b)] = len(out)
    return bytes(out), remap

# 머리 글자별 항목(실측 2026-11-06): 이름 뒤 AFS 번호와 위치
#  A 20 B: 이름 8 · 0 4 · u16 AFS · u16 SRF · u32 바이트 위치      B 16 B: 이름 4 · 0 4 · u16 AFS · u16 SRF · u32 바이트 위치
#  C 12 B: 이름 4 · 0 4 · u16 AFS · u16 위치÷4                       D  8 B: 이름 4 · u16 AFS · u16 위치÷4
FMT = {b'A': (20, 12, 16, False), b'B': (16, 8, 12, False), b'C': (12, 8, 10, True), b'D': (8, 4, 6, True)}

def idx_layout(x):
    assert x[:3] == b'IDX', x[:4]
    hl = struct.unpack_from('<I', x, 4)[0]
    assert x[hl:hl+4] == b'TABL', x[hl:hl+4]
    tl = struct.unpack_from('<I', x, hl + 4)[0]
    e = FMT[x[3:4]][0]; assert (tl - 8) % e == 0, (x[:4], tl)
    return hl + 8, (tl - 8) // e, e

def idx_rows(x):
    """[(위치 칸 자리, AFS 번호, SRF 번호 또는 None, 레코드 바이트 위치)]"""
    base, n, e = idx_layout(x); _, pa, pp, div = FMT[x[3:4]]; out = []
    for i in range(n):
        p = base + i * e; a = struct.unpack_from('<H', x, p + pa)[0]
        if div: out.append((p + pp, a, None, struct.unpack_from('<H', x, p + pp)[0] * 4))
        else: out.append((p + pp, a, struct.unpack_from('<H', x, p + pa + 2)[0], struct.unpack_from('<I', x, p + pp)[0]))
    return div, out

NOREC = 0xFFFF * 4      # 위치÷4 형식에서 «자막 없음»

def groups(rows, keys):
    """위치÷4 형식(SRF 번호 칸 없음): 음성 번호 a 는 AFS 전역 번호 — 그 음성의 SRF = a 바로 뒤에 오는 SRF(FREE 묶음은 SRF 200여 개)."""
    import bisect
    return [keys[min(bisect.bisect_left(keys, a), len(keys) - 1)] for p, a, s, o in rows]

def rebuild_idx(x, remaps):
    """remaps = {AFS 안 SRF 번호: {옛 위치: 새 위치}}. 돌려줌 (새 IDX, 못 맞춘 행 수)"""
    y = bytearray(x); div, rows = idx_rows(x); miss = 0
    keys = sorted(remaps); last = keys[-1]
    gk = groups(rows, keys) if div else None
    for i, (p, a, s, o) in enumerate(rows):
        if div and o == NOREC: continue
        k = gk[i] if div else (s if s in remaps else last)
        m = remaps[k]
        if o not in m:
            miss += 1
            continue
        n = m[o]
        if div:
            assert n % 4 == 0 and n // 4 < 0xFFFF, n
            struct.pack_into('<H', y, p, n // 4)
        else: struct.pack_into('<I', y, p, n)
    return bytes(y), miss
