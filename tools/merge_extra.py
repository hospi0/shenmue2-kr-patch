# -*- coding: utf-8 -*-
"""빠진 번역(sm2_185~189) 병합 — my files/쉔무2 → work/text/ko_extra/*.tsv + work/text/ko_extra_log.tsv
  merge_tr 의 GLOSSARY·조사·따옴표·19칸 접기를 그대로 쓰고, work/text/fix_extra.tsv(key·jp 앞부분 없이 key\tko)의 손 교정을 덮는다.
  메모 줄 9칸 넘으면 work/check/memo_over.tsv 에 적고 실패로 끝난다.
  python tools/merge_extra.py
"""
import os, sys, re, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import merge_tr as MT
from encode import normalize
SRC = os.path.join(ROOT, 'my files', '쉔무2'); ORG = os.path.join(ROOT, 'my files', 'tsv')
OUT = os.path.join(ROOT, 'work', 'text', 'ko_extra')
FIXP = os.path.join(ROOT, 'work', 'text', 'fix_extra.tsv')

TERMS = (('도리쇼', '타오리샤오'), ('내내반점', '래래반점'), ('벌레 말리기', '책 말리기'))

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, '*.tsv')): os.remove(f)
    FIX = {}
    if os.path.exists(FIXP):
        for l in open(FIXP, encoding='utf-8'):
            c = l.rstrip('\n').split('\t')
            if len(c) >= 2: FIX[c[0] if len(c) == 2 else c[0] + '|' + c[1]] = c[-1]
    log = []; over = []; dlg = []; n = 0; used = set()
    for i in range(185, 190):
        a = [l.rstrip('\r\n') for l in open(os.path.join(SRC, 'sm2_%d.tsv' % i), encoding='utf-8-sig')]
        o = [l.rstrip('\n') for l in open(os.path.join(ORG, 'sm2_%d.tsv' % i), encoding='utf-8')]
        assert len(a) == len(o), i
        out = [a[0]]
        for x, y in zip(a[1:], o[1:]):
            c = x.split('\t'); q = y.split('\t')
            assert len(c) == 5 and c[:4] == q[:4], (i, c[0])
            key, spk, cnt, jp, ko = c; before = ko
            for trig, s, t, strict in MT.GLOSSARY:
                if trig in jp and s in ko: ko = MT.replace_term(ko, s, t, strict)
            ko = MT.fix_quotes(jp, ko)
            for x_, y_ in TERMS: ko = ko.replace(x_, y_)
            if key in FIX: ko = FIX[key]; used.add(key)
            if key.startswith('memo:'):
                ko = normalize(ko.replace(' ', '　'))
                if len(ko.rstrip('　')) > 9: ko = ko.lstrip('　')      # 넘치는 줄은 들여쓰기 칸부터 뺀다
                if len(ko.rstrip('　')) > 9: over.append('%s\t%d\t%s\t%s' % (key, len(ko.rstrip('　')), jp, ko))
            else:
                L = MT.wrap(ko); ko = '＆'.join(L)
                if len(L) > 2 or any(len(z) > 19 for z in L): dlg.append('%s\t%s\t%s' % (key, jp, ko))
            if ko != before: log.append('%s\t%s\t%s' % (key, before, ko))
            c[4] = ko; out.append('\t'.join(c)); n += 1
        open(os.path.join(OUT, 'sm2_%d.tsv' % i), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    # 재배치 글꼴 칸 문자열 중 번역 묶음에서 빠진 줄(침대 메뉴 記録·設定, 기술 이름 6개) — 1편에서도 빠졌던 자리
    rk = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'text', 'remap_ko.tsv'), encoding='utf-8') if l.strip()]
    cp = os.path.join(ROOT, 'work', 'text', 'copy_ko.tsv')              # 같은 원문의 다른 주소 사본(tools/exe_copies.py)
    if os.path.exists(cp): rk += [l.rstrip('\n').split('\t') for l in open(cp, encoding='utf-8') if l.strip()]
    # 지도 지명 표 0x244 의 가나 읽기: 게임이 뒤 바이트만 반각으로 찍는다 → 빈 칸(대 = eb) 만 나오게(기술 읽기 줄과 같음). 맨 뒤에 둬서 사본·병합 값을 덮는다
    rk += [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'work', 'text', 'map_read.tsv'), encoding='utf-8') if l.strip()]
    open(os.path.join(OUT, 'sm2_190.tsv'), 'w', encoding='utf-8', newline='\n').write('key\tspeaker\tcount\tjp\tko\n' + ''.join('%s\t글꼴재배치\t1\t%s\t%s\n' % tuple(r) for r in rk))
    open(os.path.join(ROOT, 'work', 'text', 'ko_extra_log.tsv'), 'w', encoding='utf-8', newline='\n').write('key\tbefore\tafter\n' + '\n'.join(log) + '\n')
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'check', 'memo_over.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(over) + '\n')
    open(os.path.join(ROOT, 'work', 'check', 'extra_dlg_over.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(dlg) + '\n')
    print('줄 %d · 바뀐 줄 %d · 메모 넘침 %d · 대사 넘침 %d · 쓰지 않은 손 교정 %d' % (n, len(log), len(over), len(dlg), len(set(FIX) - used)))
    print('MERGE_OK' if not over and not dlg else 'MERGE_NEEDS_FIX')

if __name__ == '__main__':
    main()
