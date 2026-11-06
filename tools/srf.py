# -*- coding: utf-8 -*-
"""쉔무1 SRF 파싱(읽기 전용). 레코드 = [u32 L+이름(L-4)] [u32 L+본문(EUC-JP, NUL 패딩)(L==4 이면 없음)] [u32 L+립싱크 데이터(…FFFFFFFF)].
모든 길이 필드는 «자기 4바이트 포함». 레코드는 2048 블록을 넘지 않고, 블록 끝은 0 패딩."""
import struct
def parse_srf(b):
    out = []; p = 0
    while p + 4 <= len(b):
        L = struct.unpack_from('<I', b, p)[0]
        if L == 0:  # 2048 블록 끝 패딩 → 다음 블록
            q = (p // 2048 + 1) * 2048
            if q >= len(b) or not any(b[q:q+4]): break
            p = q; continue
        if L < 4 or L > 64 or p + L > len(b): break
        rec_off = p
        name = b[p+4:p+L].rstrip(b'\0').decode('ascii', 'replace'); p += L
        L = struct.unpack_from('<I', b, p)[0]
        raw = b[p+4:p+L]; tp = p + 4; p += L
        L2 = struct.unpack_from('<I', b, p)[0]
        if L2 < 4 or p + L2 > len(b): break
        p += L2
        text = raw.split(b'\0')[0].decode('euc_jp', 'replace') if raw else None
        out.append(dict(off=rec_off, name=name, text=text, text_off=tp, text_cap=len(raw)))
    return out, p


def split_records(b):
    """SRF → [(이름청크, 본문bytes 또는 None, 데이터청크)] (재조립용, 청크는 길이 필드 포함 원바이트)."""
    recs, end = parse_srf(b)
    out = []
    for r in recs:
        p = r['off']
        L1 = struct.unpack_from('<I', b, p)[0]; c1 = b[p:p+L1]; p += L1
        L2 = struct.unpack_from('<I', b, p)[0]; raw = b[p+4:p+L2]; p += L2
        L3 = struct.unpack_from('<I', b, p)[0]; c3 = b[p:p+L3]
        out.append((c1, raw.split(b'\0')[0] if L2 > 4 else None, c3))
    return out, end


def build_srf(recs):
    """레코드 → SRF 바이트, 레코드 시작 오프셋 목록. 규칙(원본 검산): 본문 뒤 NUL 1~4 로 4정렬,
    레코드는 2048 블록을 넘지 않는다(넘치면 0 으로 다음 블록까지 채움)."""
    out = bytearray(); offs = []
    for c1, text, c3 in recs:
        if text is None:
            c2 = struct.pack('<I', 4)
        else:
            pad = 4 - len(text) % 4
            c2 = struct.pack('<I', 4 + len(text) + pad) + text + b'\0' * pad
        rec = c1 + c2 + c3
        if len(rec) > 2048: raise ValueError('레코드 %d B > 2048' % len(rec))
        room = 2048 - len(out) % 2048
        if len(rec) > room: out += b'\0' * room
        offs.append(len(out)); out += rec
    return bytes(out), offs
