# -*- coding: utf-8 -*-
"""쉔무1 스트림 IDX(IDX0) 파싱 — 읽기 전용.
머리 16B: 'IDX0' + u16 전체 파일 수 + u16 (SRF 번호 또는 비SRF 수) + 0 + 마지막 u32(0?). 이어 20B 항목:
  이름 12B(NUL 패딩) + u16 AFS 안 파일 번호 + u16 짝 SRF 의 AFS 번호 + u32 SRF 안 레코드 오프셋."""
import struct
def parse_idx(b):
    assert b[:4] == b'IDX0', b[:4]
    h1, h2 = struct.unpack_from('<HH', b, 4)
    ents = []
    p = 20
    while p + 20 <= len(b):
        nm = b[p:p+12].split(b'\0')[0]
        if not nm: break
        fi, si, off = struct.unpack_from('<HHI', b, p+12)
        ents.append((nm.decode('ascii', 'replace'), fi, si, off)); p += 20
    return h1, h2, ents, p


def build_idx(orig, newoff):
    """원본 IDX 의 오프셋 칸만 바꾼다. newoff = {(SRF번호, 옛 오프셋): 새 오프셋}."""
    b = bytearray(orig); p = 20
    while p + 20 <= len(b) and b[p]:
        si, off = struct.unpack_from('<HI', b, p + 14)
        if si != 0xFFFF: struct.pack_into('<I', b, p + 16, newoff[(si, off)])
        p += 20
    return bytes(b)
