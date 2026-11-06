# -*- coding: utf-8 -*-
"""쉔무 II — 하스피 번역 TSV 병합 + 자동 교정 → work/text/ko/*.tsv(빌드 입력) + work/text/ko/merge_log.tsv(바꾼 것 전부)

  python tools/merge_tr.py "my files/쉔무2"

받은 폴더는 읽기만 한다. 1편 tools/merge_tr.py 에서 이름 치환·조사·따옴표 로직을 옮겨 왔다.
자동 교정(쓰는 순간 강제 — 바꾼 줄은 전부 merge_log)
  1) 실행 파일: 원문이 1편과 같은 문자열 = 1편 확정 번역(기술·아이템 이름은 하스피 통일분, 바이트 한도 맞춘 값)
  2) 이름·지명 통일(GLOSSARY, 원문 트리거 있을 때만, 뒤 조사 받침 맞춤) — 중국인 이름 = 중국어 발음(하스피 2026-11-04)
  3) 호칭: 남자 화자 오빠→형 · 어른 점원 お兄さん 오빠→손님/총각(1편 규칙)
  4) 반각 따옴표 → 원문 괄호 · 원문 『』 맞춤
  5) 실행 파일: 원문에 없는 반각 영숫자 → 전각(0 은 줄 구분, 영문자는 서식 토큰) · 續 = 글꼴 칸 II 그림 · ^S 뒤로 통일
  6) 메모장 후리가나 줄(번역 빈칸) → 전각 공백 한 칸(원문 가나가 그대로 나오지 않게)
  7) 대사: ＆ 앞뒤 공백 삭제 · 19칸×2줄 재접기(공백·문장부호 뒤에서만) · work/text/sub2_ko.tsv(손으로 줄인 줄)
  8) work/text/fix_ko.tsv: 손으로 고친 줄(key, ko, 이유) · speech_ko.tsv: 인물 말투 통일(장마다 갈린 줄)
"""
import os, sys, re, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from encode import normalize, to_wide, PUNCT

OUT = os.path.join(ROOT, 'work', 'text', 'ko')
ONE = os.path.join(ROOT, '..', 'shenmue-kr-patch', 'work', 'text', 'ko')
WIDTH, MAXLINES = 19, 2

# (원문 트리거, 틀린 꼴, 바른 꼴, 짧은 낱말이라 앞뒤 경계 필요?) — 위에서부터 차례로(긴 이름 먼저)
GLOSSARY = [
    ('鳳凰鏡', '봉황 거울', '봉황경', False), ('鳳凰の鏡', '봉황 거울', '봉황경', False), ('ホウオウキョウ', '봉황 거울', '봉황경', False),
    ('龍鏡', '용 거울', '용경', False), ('龍の鏡', '용 거울', '용경', False),
    ('刀の鍔', '칼 날밑', '칼날밑', False),
    # ── 2026-11-06 실기 지적: 대사 ↔ 그림 표기 통일
    ('桃李少', '도리 소노사', '타오리샤오 노사', False), ('桃李少', '도리쇼', '타오리샤오', False), ('桃李少', '도이소', '타오리샤오', False),
    ('方来旅社', '방래 여관', '방래여사', False), ('方来旅社', '방래여관', '방래여사', False),
    ('白酒屋台', '바이주 포장마차', '백주 포장마차', False),
    ('好運中心', '호운 센터', '러키 플라자', False), ('好運中心', '호운중심', '러키 플라자', False),
    ('不要銭宿', '불요전 숙소', '무료 숙소', False), ('香港仔', '홍콩 아자이', '애버딘', False), ('朧無双', '어렴풋한 무쌍', '몽롱무쌍', False),
    ('白秦当舗', '백진 당포', '백진전당포', False), ('白秦当舗', '백진당포', '백진전당포', False),
    ('良心当舗', '양심 당포', '양심전당포', False), ('良心当舗', '양심당포', '양심전당포', False),
    ('詠黄百貨', '영황백화점', '영황백화', False), ('詠黄百貨', '영황 백화', '영황백화', False), ('詠黄百貨', '영황백화', '영황백화점', False),
    # ── 1편 확정 이름
    ('朱元達', '주원달', '주위안다', False), ('シュゲンタツ', '주원달', '주위안다', False),
    ('藍帝', '남제', '란디', False), ('藍帝', '란 디', '란디', False), ('ランテイ', '란테이', '란디', False),
    ('桃李少', '도리소', '타오리샤오', False), ('趙孫明', '조손명', '자오쑨밍', False), ('孫明', '손명', '쑨밍', False),
    ('貴章', '귀장', '구이장', False), ('陳', '진', '첸', True), ('チン', '진', '첸', True),
    ('シェンムー', '션무', '쉔무', False), ('シェンムー', '셴무', '쉔무', False),
    # ── 주인공 쪽 (莎花 표기: 원문 가나 シェンファ·음성 기준 션화 — 1편 갤러리 【링샤화】 와 다름, 보고함)
    ('莎花', '샤화', '션화', False), ('莎花', '사화', '션화', False), ('莎花', '셴화', '션화', False),
    ('シェンファ', '셴화', '션화', False), ('シェンファ', '샤화', '션화', False),
    ('紅秀瑛', '홍수영', '홍슈잉', False), ('秀瑛', '수영', '슈잉', False), ('シュウエイ', '수영', '슈잉', False),
    ('芳梅', '방매', '팡메이', False), ('ファンメイ', '방매', '팡메이', False), ('薫', '방매', '팡메이', False),
    ('薫', '카오루', '팡메이', False), ('薫', '가오루', '팡메이', False), ('薫', '훈', '팡메이', True),
    # ── 사람 이름 = 중국어 발음
    ('張喩', '장유', '장위', False), ('チョウユ', '장유', '장위', False),
    ('玄周善', '현주선', '쉬안저우산', False), ('玄周善', '현 주선', '쉬안저우산', False),
    ('ゲンシュウゼン', '현주선', '쉬안저우산', False), ('周善', '주선', '저우산', False),
    ('建民', '건민', '젠민', False), ('桂香', '계향', '구이샹', False), ('宗泉', '종천', '쭝취안', False),
    ('漢輝', '한휘', '한후이', False), ('徳林', '덕림', '더린', False), ('洪基', '홍기', '홍지', False),
    ('小梅', '소매', '샤오메이', True), ('花梨', '카린', '화리', False), ('士全', '사전', '스취안', True),
    ('済良', '제량', '지량', False), ('姜女', '강녀', '장뉘', False), ('美夏', '미하', '메이샤', False),
    ('杜凱', '두개', '두카이', False), ('鹿鳴', '녹명', '루밍', False), ('棋瑞', '기서', '치루이', False),
    ('子谷', '자곡', '쯔구', False), ('豪亥', '호해', '하오하이', False), ('邦卓', '방탁', '방줘', False),
    ('臥羽', '와우', '워위', False), ('織雲', '직운', '즈윈', False), ('白芳', '백방', '바이팡', False),
    ('林堅', '임견', '린젠', False), ('明真', '명진', '밍전', False), ('守儀', '수의', '서우이', False),
    ('加蘭', '가란', '자란', False), ('初桂', '하쓰케이', '추구이', False), ('紫明', '자명', '쯔밍', False),
    ('斗牛', '두우', '더우뉴', False), ('凱', '가이', '카이', True), ('春燕', '춘연', '춘옌', False),
    # ── 1편 맞춤(하스피 2026-11-06 «쉔무1하고도 맞춰 용어»)
    ('蚩尤', '치우', '치유', False), ('巌', '간', '이와오', True), ('河緑石', '河緑石', '하록석', False),
    ('手技', '손 기술', '손기술', False), ('足技', '발 기술', '발기술', False), ('コイン', '동전', '코인', False),
    ('チンピラ', '건달', '깡패', False), ('チンピラ', '불량배', '깡패', False), ('薬屋', '약방', '약국', True),
    # ユアン = 위안(朱元達 주위안다의 元과 같은 발음, 유안·위안 혼용)
    ('ユアン', '유안', '위안', False),
    # ── 1편 tools/merge_tr.py GLOSSARY 그대로

    ('稲', '이나', '이네', True), ('陳', '진', '첸', True), ('陳', '천', '첸', True), ('劉', '유', '류', True),
    ('大石', '오오이시', '오이시', False), ('矢田', '야타', '야다', False),
    ('クリタ', '구리타', '쿠리타', False), ('栗田', '구리타', '쿠리타', False),
    ('明田川', '아케다가와', '아케타가와', False), ('竹内', '다케우치', '타케우치', False),
    ('辰巳', '다쓰미', '타츠미', False), ('辰巳', '타쓰미', '타츠미', False), ('タツミ', '타쓰미', '타츠미', False),
    ('住谷', '스미타니', '스미야', False), ('鶴岡', '쓰루오카', '츠루오카', False), ('ツルオカ', '쓰루오카', '츠루오카', False),
    ('コミネ', '고미네', '코미네', False), ('小峰', '고미네', '코미네', False), ('秀玉', '슈교쿠', '수옥', False),
    ('貴章', '키쇼', '귀장', False), ('貴章', '다카아키', '귀장', False), ('藍帝', '남제', '란디', True),
    ('原崎', '하라자키', '하라사키', False), ('八百勝', '야오카쓰', '야오카츠', False), ('勝', '가쓰', '카츠', True),
    ('つくし', '쓰쿠시', '츠쿠시', False), ('土蜘蛛', '쓰치구모', '츠치구모', False), ('松山', '마쓰야마', '마츠야마', False),
    ('小松菜', '고마쓰나', '코마츠나', False), ('イシマツ', '이시마쓰', '이시마츠', False), ('こたつ', '고타쓰', '코타츠', False),
    ('草津', '쿠사쓰', '쿠사츠', False), ('残月', '잔게쓰', '잔게츠', False), ('ミツヅカ', '미쓰즈카', '미츠즈카', False),
    ('はつてん', '하쓰텐', '하츠텐', False), ('シュゲンタツ', '슈겐타쓰', '슈겐타츠', False),
    ('リュウサツ', '류사쓰', '류사츠', False),
    ('トキ', '도키', '토키', True), ('シェンムー', '션무', '쉔무', False),
    # 중국인 이름 = 중국어 발음(하스피 2026-11-04 «중국인 이름은 중국어 발음으로»)
    ('陶', '도', '타오', True), ('チンタイジン', '천', '첸', True),
    ('貴章', '귀장', '구이장', False), ('貴章', '타카아키', '구이장', False), ('秀玉', '하수옥', '샤슈위', False), ('秀玉', '수옥', '슈위', False),
    ('朱元達', '주원달', '주위안다', False), ('朱元達', '朱元達', '주위안다', False), ('シュゲンタツ', '슈겐타츠', '주위안다', False),
    ('高文', '타카후미', '가오원', False), ('高文', '코타', '가오원', True), ('コウブン', '高文', '가오원', False),
    ('趙孫明', '조손명', '자오쑨밍', False), ('趙', '조', '자오', True),
    ('桃李少', '도리소', '타오리샤오', False), ('桃李少', '桃李少', '타오리샤오', False), ('かよこ', '가요코', '카요코', False), ('タムラ', '다무라', '타무라', False),
    # 게임 내부 가나 낱말
    ('ケンカアッパー', '싸움 어퍼', '싸움 어퍼컷', False), ('喧嘩アッパー', '싸움 어퍼', '싸움 어퍼컷', False),
    ('湾仔', '만자', '완차이', False),
    ('オンタ”ロウ', '온다루', '은전루', False), ('方来旅社', '방래 여사', '방래여사', False),
    ('シュケ”ンタツ', '주원달', '주위안다', False), ('ケンミン', '건민', '젠민', False), ('ケイカ', '계향', '구이샹', False),
    ('トウリショウ', '도리소', '타오리샤오', False), ('キショウ', '귀장', '구이장', False), ('桂林', '구이린', '계림', False), ('ケイリン', '구이린', '계림', False),
    ('ライライハンテン', '라이라이 반점', '래래반점', False), ('オトシダマ', '오토시다마', '구슬 떨구기', False),
    ('シュンエン', '춘연', '춘옌', False), ('トギュー', '두우', '더우뉴', False),
    # ── 표기 갈림(가나 이름)
    ('ヤン', '양', '얀', True), ('アイリン', '아이링', '아이린', False), ('ハッサン', '하산', '핫산', False),
    ('グレッグ', '그레그', '그렉', False),
    # ── 지명·가게(실제 도시 = 통용 표기, 가상 거리 = 번역 그대로의 한자음에서 다수 표기로)
    ('点心街', '점심가', '딤섬가', False), ('点心街', '딤섬 거리', '딤섬가', False), ('点心楼', '점심루', '딤섬루', False),
    ('飲茶楼', '얌차루', '음다루', False), ('飲茶楼', '음차루', '음다루', False),
    ('開運碼頭', '개운마두', '개운 부두', False), ('開運碼頭', '개운부두', '개운 부두', False),
    ('労湾碼頭', '노만마두', '노만 부두', False), ('労湾碼頭', '노만부두', '노만 부두', False), ('労湾碼頭', '로만 부두', '노만 부두', False),
    ('三刀小路', '삼도소로', '삼도 골목', False), ('三刀小路', '삼도골목', '삼도 골목', False), ('三刀小路', '산토 골목', '삼도 골목', False),
    ('恩田楼', '온다루', '은전루', False),
    ('来来飯店', '내래반점', '래래반점', False), ('来来飯店', '라이라이 반점', '래래반점', False), ('来来飯店', '라이라이반점', '래래반점', False),
    ('ビバリーヒルズ', '비벌리 힐스', '비벌리힐스', False), ('ビバリーヒルズ', '베벌리힐스', '비벌리힐스', False),
    ('ビバリーヒルズ', '베벌리 힐스', '비벌리힐스', False), ('ビバリーヒルズ', '비버리 힐스', '비벌리힐스', False),
    ('ビバリーヒルズ', '비버리힐스', '비벌리힐스', False), ('ワーフ', '와프', '워프', False),
    ('クイーンズ', '퀸스', '퀸즈', False), ('キングスロード', '킹스로드', '킹스 로드', False),
    ('鈴鈴', '영령죽전과', '영령 죽 전문점', False), ('鈴鈴', '령령죽', '영령 죽', False), ('鈴鈴', '영령죽', '영령 죽', False),
    ('茶碗陣', '다완진', '찻잔진', False), ('茶碗陣', '차완진', '찻잔진', False), ('茶碗陣', '찻잔 진', '찻잔진', False),
    ('屋台街', '노점가', '포장마차 거리', False), ('屋台街', '노점 거리', '포장마차 거리', False), ('屋台街', '포장마차가', '포장마차 거리', True),
    ('白千屋台', '백천포장마차', '백천 포장마차', False), ('龍泉屋台', '용천포장마차', '용천 포장마차', False),
    ('紅南街', '홍남 거리', '홍남가', False), ('太老街', '태로 거리', '태로가', False),
    ('アームレスリング', '암 레슬링장', '팔씨름장', False), ('アームレスリング', '암레슬링장', '팔씨름장', False), ('アームレスリング', '레슬링장', '팔씨름장', False),
    ('ガチャガチャ', '가챠가챠', '뽑기', False),
    # 落し玉 = 구슬 떨구기(오토시다마·낙옥·구슬 떨어뜨리기·구슬 도박 혼용 — 짧은 표기로, 줄 폭 때문)
    ('落', '구슬 떨어뜨리기', '구슬 떨구기', False), ('落', '구슬떨어뜨리기', '구슬 떨구기', False), ('落', '오토시다마', '구슬 떨구기', False),
    ('落', '낙옥', '구슬 떨구기', False), ('落し玉', '떨어뜨리기 게임', '구슬 떨구기', False), ('落し玉', '구슬 도박', '구슬 떨구기', False),
    ('オトシダマ', '구슬 떨어뜨리기', '구슬 떨구기', False),
    ('ュージアム', '박물관', '뮤지엄', False),
    ('そば屋', '일본 국숫집', '소바집', False), ('そば屋', '국숫집', '소바집', False), ('そば屋', '국수집', '소바집', False),
    ('楽宴茶荘', '낙연차장', '낙연다장', False), ('楽宴茶荘', '락연다장', '낙연다장', False),
    ('電器小路', '전기소로', '전기 골목', False), ('アームレスリング', '암레슬링', '팔씨름', False),
    ('胴元', '판주', '물주', False), ('胴元', '업주', '물주', False), ('胴元', '떨구기 주인', '떨구기 물주', False), ('胴元', '떨구기의 주인', '떨구기 물주', False),
    ('菜珍街', '채진 거리', '채진가', False), ('詠黄街', '영황 거리', '영황가', False), ('白秦街', '백진 거리', '백진가', False),
    ('白千街', '백천 거리', '백천가', False), ('福仙街', '복선 거리', '복선가', False), ('龍影街', '용영 거리', '용영가', False),
]

# 남자 화자 お兄ちゃん(오빠→형) — 원문이 여럿이 같이 쓰는 줄은 fix_ko 에서 호칭 없는 문장으로
MALE_KEYS = ('FEX10B085', 'FEX10B086', 'FEX10B087', 'FEX10B116')
# 어른 가게·도박장 여자가 료를 부르는 お兄さん/お兄ちゃん: 화자 → 호칭
ADULT_CALL = {'DM1': '손님', 'PG5': '손님', 'MFG': '손님', 'EYR': '손님', 'MMH': '손님', '石': '손님', '桃': '손님',
              '栄伶': '손님', '光美': '손님', '蘭芳': '총각', '華潤': '총각'}

def jong(ch):
    o = ord(ch) - 0xAC00
    return (o % 28) if 0 <= o < 11172 else None
JOSA = [('이에요', '예요'), ('이야', '야'), ('이랑', '랑'), ('이나', '나'), ('으로', '로'), ('은', '는'), ('을', '를'), ('과', '와'), ('이', '가')]
_JR = '|'.join(sorted({x for p in JOSA for x in p}, key=len, reverse=True))
def fit(word, jo):
    j = jong(word[-1])
    for c, v in JOSA:
        if jo in (c, v):
            if c == '으로': return '로' if j in (0, 8) else '으로'
            return v if j == 0 else c
    return jo

def replace_term(t, a, b, strict):
    pre = r'(?<![가-힣])' if strict else ''
    def sub(m):
        jo, nx = m.group(1), m.group(2)
        if strict and nx and jong(nx) is not None and not jo and nx not in '의에한랑께씨네만': return m.group(0)      # 뒤가 한글(조사 아님) → 다른 낱말
        if jo is None: return b
        if jo in ('이', '가', '이야', '야') and nx and jong(nx) is not None: return b + jo
        return b + fit(b, jo)
    t = re.sub(pre + re.escape(a) + '(' + _JR + ')?(?=(.?))', sub, t)
    tail_c = '냐|라는|라고|라면|란|라서|라도|라니|였|예요|여서|지만|면서|다|며|고|네|군|구나|니까|잖'
    if jong(b[-1]) and not jong(a[-1]):                       # 받침 생김: 서술격 «냐·라는…» 앞에 «이»
        t = re.sub(re.escape(b) + '(?=냐|라는|라고|라면|란|라서|라도|라니|였|예요|여서)', b + '이', t)
    if jong(a[-1]) and not jong(b[-1]):                       # 받침 사라짐: «주원달이라는» → «주위안다라는»
        t = re.sub(re.escape(b) + '이(?=냐|라는|라고|라면|란|라서|라도|라니|었|에요|여서|지만|면서|다[.!?…,]|다$|며|고[ ,]|네|군|구나|니까|잖)', b, t)
    return t

def fix_quotes(jp, ko):
    if "'" not in ko and '"' not in ko: return ko
    o, c = ('『', '』') if '『' in jp else ('「', '」')
    for q in ("'", '"'):
        parts = ko.split(q)
        if len(parts) % 2 == 1:
            ko = ''.join(p + ((o if i % 2 == 0 else c) if i < len(parts) - 1 else '') for i, p in enumerate(parts))
    return ko

# ── 19칸×2줄 재접기 ────────────────────────────────────────────
_BRK = re.compile('[ 　]+|(?<=[%s])(?=[^ 　%s])' % (re.escape(',.!?…、。，．！？」』'), re.escape(PUNCT)))
def wrap(ko):
    """돌려줌: 줄 목록. 번역자 ＆ 가 맞으면 그대로, 아니면 공백·문장부호 뒤 자리 중 둘 다 19칸 이내인 곳(원래 ＆ 자리에 가장 가까운 곳)."""
    ko = normalize(ko)
    parts = [p.strip(' 　') for p in ko.split('＆')]
    if len(parts) <= MAXLINES and all(len(p) <= WIDTH for p in parts): return parts
    flat = ' '.join(parts) if all(not p or p[-1] not in PUNCT for p in parts[:-1]) else ''
    if not flat:                                              # 부호로 끝난 줄 뒤엔 공백 없이 잇기(부호 뒤 공백 규칙)
        flat = parts[0]
        for p in parts[1:]: flat += ('' if flat and flat[-1] in PUNCT else ' ') + p
    flat = normalize(flat)
    if len(flat) <= WIDTH: return [flat]
    want = len(parts[0])
    best = None
    for m in _BRK.finditer(flat):
        a, b = flat[:m.start()], flat[m.end():]
        if not a or not b or len(a) > WIDTH or len(b) > WIDTH: continue
        if b[0] in PUNCT: continue
        sc = abs(len(a) - want)
        if best is None or sc < best[0]: best = (sc, [a, b])
    if best: return best[1]
    # 못 맞춤: 탐욕 접기(3줄 이상 그대로 보고)
    lines = ['']
    for w in re.split(r'[ 　]', flat):
        c = (lines[-1] + ' ' + w) if lines[-1] else w
        if len(c) <= WIDTH or not lines[-1]: lines[-1] = c
        else: lines.append(w)
    return lines

# ── 실행 파일 ──────────────────────────────────────────────────
def fix_exe_alnum(jp, ko):
    """원문의 반각 토큰(^S·3·A·L·G2…)만 반각으로 두고, 나머지 반각 영숫자는 전각 — 반각 0 은 줄 구분·영문자는 서식으로 읽힌다."""
    if re.search(r'[A-Za-z]{3}', jp): return ko                 # 지명 영문 짝(Langhui Shop) — 원문이 반각 글자
    pool = collections.Counter(re.findall(r'\^?[0-9A-Za-z]+', jp))
    for run in list(pool):                                      # 숫자·문자 토큰 낱낱도 허용
        for ch in run:
            pool[ch] += pool[run]
    def f(m):
        r = m.group()
        if pool[r] > 0: pool[r] -= 1; return r
        if all(pool[ch] > 0 for ch in r): return r
        return ''.join(to_wide(ch) for ch in r)
    return re.sub(r'\^?[0-9A-Za-z]+', f, ko)

RUBY = re.compile(r'^　*[ぁ-ゖァ-ヺ”ー]+　*$')

def load_tsv(name):
    p = os.path.join(ROOT, 'work', 'text', name); m = {}
    if os.path.exists(p):
        for l in open(p, encoding='utf-8').read().splitlines()[1:]:
            c = l.split('\t')
            if len(c) >= 2 and c[0]: m[c[0]] = (c[1], c[2] if len(c) > 2 else '')
    return m

# 1편 번역을 쓰지 않는 실행 파일 문자열(1편 쪽이 어색하거나 II 번역이 나은 것)
# 기술 낱자 표(0x2529C8, 12 B 행 {이름, SPR, 칸 크기}, 함수 0x1A4240): 이름을 strcmp 로 찾고 strlen÷2 를 칸 수로 쓴다.
# 부르는 쪽 이름은 일본어 그대로 넘어온다(같은 문자열이 실행 파일엔 이 표뿐, 나머지는 장면 데이터) → 표 이름을 번역하면 낱자가 안 뜬다. 화면엔 그림으로만 나옴.
NAME_LOCK = {'exe:22603C', 'exe:226028', 'exe:226014', 'exe:225FFC', 'exe:225FE8', 'exe:225FD4', 'exe:225FC0', 'exe:225FA4', 'exe:225F8C', 'exe:225F7C', 'exe:225F6C', 'exe:225F5C', 'exe:225F4C'}
ONE_KEEP = {'ニワサキ', '庭先', 'ランテイ', '桂林', 'ケイリン'}   # 桂林: 1편 자막이 계림(1편 실행 파일 낱말만 구이린)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = sys.argv[1]
    one = {}
    for f in glob.glob(os.path.join(ONE, 'sm1_*.tsv')):
        for l in open(f, encoding='utf-8').read().split('\n')[1:]:
            c = l.split('\t')
            if len(c) > 4 and c[0].startswith('exe:') and c[4].strip(): one[c[3]] = c[4]
    WD = {}                                  # 기술 설명 다시 쓴 표(key 없이 주소) — 사전 낱말을 잇지 않고 풀어 쓴 문장, 21칸 # 21칸
    for l in open(os.path.join(ROOT, 'work', 'text', 'waza_desc.tsv'), encoding='utf-8'):
        c = l.rstrip('\n').split('\t'); WD['exe:' + c[0]] = c[1]
    FIX = load_tsv('fix_ko.tsv'); SUB2 = load_tsv('sub2_ko.tsv'); SPEECH = load_tsv('speech_ko.tsv'); SUB2.update(SPEECH)
    used = set()
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, '*.tsv')): os.remove(f)
    log = ['file\tkey\twhy\tbefore\tafter']; over = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'tsv', '*.tsv'))):
        base = os.path.basename(f)[:-4]
        cand = glob.glob(os.path.join(src, base + '*.tsv'))
        assert len(cand) == 1, (base, cand)
        lines = [l.rstrip('\r\n') for l in open(cand[0], encoding='utf-8-sig')]
        orig = [l.rstrip('\n') for l in open(f, encoding='utf-8')]
        assert len(lines) == len(orig), base
        out = [lines[0]]
        for ln, lo in zip(lines[1:], orig[1:]):
            c = ln.split('\t'); o = lo.split('\t')
            assert len(c) == 5 and c[:4] == o[:4], (base, c[0])
            key, spk, cnt, jp, ko = c
            before = ko; why = []; isexe = key.startswith('exe:')
            if key in NAME_LOCK:
                if ko.strip(): log.append('%s	%s	기술 낱자 표 이름 — 일본어 고정	%s	' % (base, key, ko))
                c[4] = ''; out.append('	'.join(c)); continue
            if isexe and not ko.strip() and RUBY.match(jp):
                ko = '　'; why.append('메모장 후리가나 줄 → 빈칸')
            elif not ko.strip():
                out.append(ln); continue
            if isexe and jp in one and jp not in ONE_KEEP and one[jp] != ko:
                ko = one[jp]; why.append('1편 확정 번역')
            for trig, a, b, strict in GLOSSARY:
                if trig in jp and a in ko:
                    n = replace_term(ko, a, b, strict)
                    if n != ko: ko = n; why.append('이름 %s→%s' % (a, b))
            if key in MALE_KEYS and '오빠' in ko:
                ko = replace_term(ko, '오빠', '형', False); why.append('남자 화자 오빠→형')
            if spk in ADULT_CALL and '오빠' in ko and re.search('兄', jp):
                ko = replace_term(ko, '오빠', ADULT_CALL[spk], False); why.append('어른 점원 호칭 오빠→' + ADULT_CALL[spk])
            n = fix_quotes(jp, ko)
            if n != ko: ko = n; why.append('반각 따옴표→원문 괄호')
            if '『' in jp and '「' not in jp and '『' not in ko and ko.count('「') == jp.count('『'):
                ko = ko.replace('「', '『').replace('」', '』'); why.append('「」→원문 『』')
            if key in FIX: ko = FIX[key][0]; why.append('손 교정: ' + FIX[key][1]); used.add(key)
            if key in WD: ko = WD[key]; why.append('기술 설명 다시 씀')
            if key.startswith('exe:') and 0x22605C <= int(key[4:], 16) <= 0x2266EC and re.fullmatch('[ァ-ヶー]+', jp):
                ko = '대'; why.append('기술 읽기 줄: 뒤 바이트를 반각으로 찍는다 — 빈 칸(eb)만 나오게')
            if isexe:
                if '續' in jp:
                    n = re.sub(r' ?(?:II|Ⅱ|２|속)(?=】)', '續', ko)
                    if n != ko: ko = n; why.append('續 = 글꼴 칸 II 그림')
                n = ko.replace('돌아가기', '뒤로') if '戻る' in jp else ko
                if n != ko: ko = n; why.append('^S 뒤로 통일')
                n = fix_exe_alnum(jp, ko)
                if n != ko: ko = n; why.append('원문에 없는 반각 영숫자→전각')
            else:
                if key in SUB2: ko = SUB2[key][0]; why.append('말투 통일: ' + SPEECH[key][1] if key in SPEECH else '줄이기: 19칸×2줄'); used.add(key)
                L = wrap(ko); n = '＆'.join(L)
                if len(L) > MAXLINES or any(len(x) > WIDTH for x in L):
                    over.append('%s\t%s\t%s\t%d줄/%d칸\t%s\t%s' % (base, key, spk, len(L), max(map(len, L)), jp, n))
                if n != ko:
                    why.append('19칸 재접기' if [len(x) for x in re.sub('[ 　]', '', normalize(ko)).split('＆')] != [len(x) for x in re.sub('[ 　]', '', n).split('＆')] else '부호 뒤·줄 끝 공백 정리')
                    ko = n
            if ko != before: log.append('%s\t%s\t%s\t%s\t%s' % (base, key, ' · '.join(why) or '공백 정리', before, ko))
            c[4] = ko; out.append('\t'.join(c))
        open(os.path.join(OUT, base + '.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    open(os.path.join(OUT, 'merge_log.tsv'), 'w', encoding='utf-8', newline='\n').write('\n'.join(log) + '\n')
    os.makedirs(os.path.join(ROOT, 'work', 'check'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'check', 'overflow.tsv'), 'w', encoding='utf-8', newline='\n').write('file\tkey\tspk\tsize\tjp\tko\n' + ''.join(x + '\n' for x in over))
    miss = (set(FIX) | set(SUB2)) - used
    if miss: print('⚠ 손 교정 키 못 찾음:', sorted(miss)[:20])
    c = collections.Counter(re.sub(r'이름 .*', '이름 통일', w) for l in log[1:] for w in l.split('\t')[2].split(' · '))
    for k, n in c.most_common(): print('%6d  %s' % (n, k[:40]))
    print('바꾼 줄 %d · 넘침 남음 %d → %s' % (len(log) - 1, len(over), OUT))

if __name__ == '__main__':
    main()
