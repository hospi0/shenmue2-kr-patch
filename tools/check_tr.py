# -*- coding: utf-8 -*-
"""쉔무 II 병합본 전수 검사 — python tools/check_tr.py → work/check/check_report.tsv · speech_mix.tsv
 오류: 키·원문 변경, 자막 19칸×2줄, 메모 9칸, 아이템 이름 18 B, 제어 토큰, 괄호(PKS 끝 」 오타 제외), 가나, EUC 못 넣는 글자
 경고: 이름 뒤 조사 받침 · 옛 표기 잔여 / speech_mix: 인물 다수 어미와 다른 줄 중 원문 어조는 다수와 같은 줄"""
import os, sys, re, glob, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from encode import normalize, SUBST, to_wide
W = lambda *a: os.path.join(ROOT, 'work', *a)
ITEM = ((0x23e02c, 23), (0x23e20c, 33), (0x23e658, 279), (0x23fd14, 26))   # 20 B 행, +12 이름
MEMO = (0x21F000, 0x220800)
LOCK = {'exe:22603C', 'exe:226028', 'exe:226014', 'exe:225FFC', 'exe:225FE8', 'exe:225FD4', 'exe:225FC0', 'exe:225FA4', 'exe:225F8C', 'exe:225F7C', 'exe:225F6C', 'exe:225F5C', 'exe:225F4C'}
NAMES = '주위안다 슈잉 션화 팡메이 장위 저우산 젠민 구이샹 쭝취안 한후이 더린 홍지 샤오메이 화리 스취안 지량 장뉘 메이샤 두카이 루밍 치루이 쯔구 하오하이 방줘 워위 즈윈 바이팡 린젠 밍전 서우이 자란 추구이 쯔밍 더우뉴 카이 춘옌 위안 타오리샤오 자오쑨밍 란디 구이장 이와오 하라사키'.split()
OLD = '주원달 홍수영 방매 도리소 조손명 귀장 남제 샤화 셴화 치우문 하라자키 얌차루 음차루 오토시다마 낙옥 개운마두 노만마두 삼도소로 내래반점 다완진 온다루'.split()
def jong(c): return (ord(c) - 0xAC00) % 28
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rep = []; R = []
    for f in sorted(glob.glob(W('text', 'ko', 'sm2_*.tsv'))):
        b = os.path.basename(f); o = open(W('text', 'tsv', b), encoding='utf-8').read().split('\n')
        u = open(f, encoding='utf-8').read().split('\n')
        if len(o) != len(u): rep.append(('오류', b, '', '행 수', '', ''))
        for x, y in zip(o[1:], u[1:]):
            if not y: continue
            c = y.split('\t')
            if len(c) != 5 or c[:4] != x.split('\t')[:4]: rep.append(('오류', b, c[0], '키·원문', '', y)); continue
            R.append((b, *c))
    d = open(W('disc1', '1ST_READ.BIN'), 'rb').read(); items = set()
    for o, n in ITEM:
        for i in range(n): items.add(struct.unpack_from('<I', d, o + i * 20 + 12)[0] - 0x8C010000)
    def E(sev, r, what): rep.append((sev, r[0], r[1], what, r[4], r[5]))
    empty = 0
    for r in R:
        b, key, spk, cnt, jp, ko = r
        if key in LOCK and ko.strip(): E('오류', r, '기술 낱자 표 이름은 일본어 고정')
        if not ko.strip():
            empty += 1; E('알림', r, '번역 빈칸'); continue
        exe = key.startswith('exe:')
        if re.search('[ぁ-ヺ]', ko): E('오류', r, '가나 남음')
        for ch in set(normalize(ko)):
            if ord(ch) > 0x7e and not ('가' <= ch <= '힣') and ch != '＆':
                try: to_wide(ch).encode('euc_jp')
                except UnicodeEncodeError: E('오류', r, 'EUC 못 넣음 %r' % ch)
        if exe:
            off = int(key[4:], 16)
            tok = lambda s: [x.replace('0', '') for x in re.findall(r'\^?[0-9A-Za-z]+', s) if x.replace('0', '')]
            if not re.search(r'[A-Za-z]{3}', jp) and tok(jp) != tok(ko) and not (set(tok(ko)) <= set(tok(jp))): E('오류', r, '제어 토큰')
            if jp.count('＼ｔ') != ko.count('＼ｔ'): E('오류', r, '탭 수')
            if MEMO[0] <= off < MEMO[1] and len(ko) > 9: E('오류', r, '메모 9칸 넘침')
            if off in items and len(ko.strip()) * 2 > 18: E('오류', r, '아이템 18 B 넘침')
        else:
            L = ko.split('＆')
            if len(L) > 2 or any(len(x) > 19 for x in L): E('오류', r, '자막 19칸×2줄 넘침')
            if ko != '＆'.join(x.strip(' 　') for x in L) and not re.search('　$', jp): E('경고', r, '줄 앞뒤 공백')
            for a in '「『』':
                if jp.count(a) != ko.count(a): E('경고', r, '괄호 ' + a)
        for w in OLD:
            if w in ko: E('경고', r, '옛 표기 ' + w)
        for w in NAMES:
            for m in re.finditer(re.escape(w) + '(이|가|을|를|은|는|과|와|으로|로)(?=[ 　＆,.!?…]|$)', ko):
                j = jong(w[-1]); t = m.group(1)
                ok = {'이': j, '을': j, '은': j, '과': j, '가': not j, '를': not j, '는': not j, '와': not j, '으로': j and j != 8, '로': (not j) or j == 8}[t]
                if not ok: E('오류', r, '이름 뒤 조사 %s%s' % (w, t))
    # 말투
    spk = collections.defaultdict(collections.Counter)
    for l in open(W('text', 'lines.tsv'), encoding='utf-8'):
        k, key, s, jp = l.split('\t')[:4]
        if k == 'pks' and '「' in jp:
            jp = jp.split('「', 1)[1]; jp = jp[:-1] if jp.endswith('」') else jp
        spk[jp][s] += 1
    def cls(ko):
        t = re.sub(r'[…!?！？.,~〜～」』\s　ー]+$', '', ko.split('＆')[-1])
        if re.search(r'(니다|니까|십시오|시죠|요|죠)$', t) and not re.search(r'[으]?니까$', t) or re.search('[습입]니까$', t): return '존'
        if re.search(r'(다|야|어|아|지|해|냐|니|까|자|라|걸|래|군|마|거든|잖아|네|나|게|구나|구먼|세|오)$', t): return '평'
    def jcls(jp):
        t = re.sub(r'[…！？。、ー〜っッ」』\s　]+$', '', jp.split('＆')[-1])
        if re.search(r'(です|ます|ました|ません|ください|でしょう|ですか|ますか|ませんか|ですよ|ますよ|ですね|ますね|ですが|ますが)[よねか]?$', t): return '존'
        if re.search(r'(だ|だよ|だね|だな|だぜ|ぜ|な|ぞ|さ|かい|かな|だろ|だろう|よ|ね|の|わ|じゃ|のう|ねえ)$', t): return '평'
    per = collections.defaultdict(collections.Counter); rows = collections.defaultdict(list)
    for r in R:
        if r[1].startswith('exe:') or not r[5].strip(): continue
        c = cls(r[5]); sp = spk[r[4]]
        if c and len(sp) == 1:
            s = next(iter(sp)); per[s][c] += 1; rows[s].append((c, r))
    mix = []
    for s, c in per.items():
        if s in ('涼', 'RYO') or '①' in s or sum(c.values()) < 12: continue
        maj = '존' if c['존'] >= c['평'] else '평'
        if c[maj] / sum(c.values()) < .7: continue
        for k, r in rows[s]:
            if k != maj and jcls(r[4]) == maj: mix.append('%s\t%s\t%s\t%s\t%s\t%s' % (s, maj, r[0], r[1], r[4], r[5]))
    open(W('check', 'speech_mix.tsv'), 'w', encoding='utf-8', newline='\n').write('화자\t다수\t파일\tkey\tjp\tko\n' + '\n'.join(mix) + '\n')
    open(W('check', 'check_report.tsv'), 'w', encoding='utf-8', newline='\n').write('sev\tfile\tkey\twhat\tjp\tko\n' + ''.join('\t'.join(x) + '\n' for x in rep))
    c = collections.Counter((x[0], x[3].split(' ')[0]) for x in rep)
    print('줄', len(R), '· 빈칸', empty)
    for k, n in sorted(c.items()): print(k, n)
    print('말투 흔들림(원문 어조는 다수와 같음)', len(mix))
if __name__ == '__main__': main()
