# -*- coding: utf-8 -*-
"""1ST_READ.BIN SH-4 역어셈블 (건버드2 tools/sh4dis.py → 쉔무, 2026-11-03). 테라 sh2_disasm 에 워드를 뒤집어 넣는다.
FPU·SH-4 전용은 «?» 로 나올 수 있다. 적재 0x8C010000(데이터 포인터는 0x0C010000 꼴로 저장됨).
  python tools/sh4dis.py 파일오프셋(16진) [개수]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
LOAD = 0x8C010000
EXE = os.path.join(ROOT, 'work', 'disc1', '1ST_READ.BIN')
_src = open(r'C:\claude\project\terra-kr-patch\tools\sh2_disasm.py', encoding='utf-8').read().split("if __name__")[0]
_ns = {}; exec(_src, _ns)
_G = None
def dis(off, n=80, g=None):
    global _G
    g = g or _G or open(EXE, 'rb').read(); _G = g
    raw = g[off:off + n * 2]
    be = b''.join(raw[i + 1:i + 2] + raw[i:i + 1] for i in range(0, len(raw) - 1, 2))
    return ['%06X  %04X  %s' % (a - LOAD, w, t) for a, w, t in _ns['disasm_sh2'](be, LOAD + off, n)]
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(dis(int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 80)))
