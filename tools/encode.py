# -*- coding: utf-8 -*-
"""번역문 → 게임 바이트(EUC 2바이트). build_font.py 의 칸 배치와 짝.

  · 한글(완성형) → EUC-KR 바이트 그대로(= JIS 16~40구 칸) / 완성형 밖 → work/font/extra_map.tsv
  · 나머지 → EUC-JP. 반각 기호·영숫자는 전각으로 바꿔 넣는다(반각 글꼴 쪽 표시는 미확인).
  · 전프로젝트 규칙(쓰는 순간 강제): 「……」「...」→「…」 한 칸 / 문장부호 뒤 공백 삭제
  · 줄바꿈 = 「＆」 (SRF), 공백 = 전각 공백(　) — 반각 공백 폭은 실기 확인 후 결정
"""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
EXTRA = os.path.join(ROOT, 'work', 'font', 'extra_map.tsv')
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'   # ★전프로젝트 표준 문장부호 목록(메모리 feedback_no_space_after_punct)

def _extra():
    m = {}
    if os.path.exists(EXTRA):
        for ln in open(EXTRA, encoding='utf-8'):
            ch, code = ln.rstrip('\n').split('\t'); m[ch] = bytes.fromhex(code)
    return m
_EX = None

def normalize(s):
    s = re.sub(r'(?:…|\.\.\.|・・・)+', '…', s)
    s = re.sub('([%s])[ 　](?![ 　])' % re.escape(PUNCT), r'\1', s)    # 부호 바로 뒤 공백 1칸(반각·전각) — 2칸 이상은 칸 맞춤이라 둠
    return s

# EUC-JP(파이썬 euc_jp)에 없는데 번역에 흔히 나오는 글자 → 받는 모양 (전각 변환 «뒤»에 적용)
SUBST = {'—': '―', '–': '―', '－': '−', '～': '〜',
         '·': '・', '‧': '・'}

def to_wide(ch):
    o = ord(ch)
    if ch == ' ': return '　'
    if 0x21 <= o <= 0x7E: ch = chr(o + 0xFEE0)
    return SUBST.get(ch, ch)

def encode(s, half_space=False, half_ascii=False):
    """half_space: 공백을 반각 0x20(반각 글꼴 DC_KANA 칸)으로 / half_ascii: 영숫자·기호도 반각 1바이트로 (시험 중)"""
    global _EX
    _EX = _EX if _EX is not None else _extra()
    out = bytearray()
    for ch in normalize(s):
        if ch in _EX and not ('가' <= ch <= '힣' and len(ch.encode('euc_kr', 'ignore')) == 2):
            out += _EX[ch]; continue                   # 완성형 밖 음절 · 한글 칸에 덮인 한자(build_font 가 41구 이후로 옮김)
        if '가' <= ch <= '힣':
            b = ch.encode('euc_kr')          # ⚠ 완성형 밖은 파이썬이 8바이트 조합 시퀀스로 내준다
            if len(b) == 2: out += b
            elif ch in _EX: out += _EX[ch]
            else: raise ValueError('완성형 밖 음절 %r — build_font.py --extra 에 넣을 것' % ch)
        elif (ch == ' ' and half_space) or (half_ascii and 0x21 <= ord(ch) <= 0x7E):
            out += ch.encode('ascii')
        else:
            b = to_wide(ch).encode('euc_jp')
            if len(b) != 2: raise ValueError('2바이트가 아닌 글자 %r' % ch)
            out += b
    return bytes(out)

if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8')
    for t in ['료는 그 남자를... 찾아!! 뷁', '아, 그래?  그렇군……', 'ABC 123']:
        b = encode(t); print(t, '→', b.hex(' '))
