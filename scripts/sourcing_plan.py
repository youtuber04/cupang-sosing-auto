"""소싱 순서 관리 — 1단계 최근 1달 카테고리별 인기 → 2단계 2달 뒤 카테고리별 인기 → 3단계 계절 상관없는 욕실·주방·거실 용품.
부피가 크고 무거운 제품(침대·소파·식탁·옷장 등)은 모든 단계에서 뺀다.

사용(스킬 폴더에서):
  python scripts/sourcing_plan.py next              → 지금 단계·카테고리와 검색어 후보를 보여 준다
  python scripts/sourcing_plan.py done "<카테고리>"  → 그 카테고리 소싱 완료(다음 카테고리로)
  python scripts/sourcing_plan.py skip "<카테고리>"  → 쓸 상품이 없어 건너뜀
  python scripts/sourcing_plan.py check "<상품명>"   → 부피 큰 제품인지 검사(제외면 종료 코드 3)
  python scripts/sourcing_plan.py status            → 진행 상황
  python scripts/sourcing_plan.py reset             → 처음부터(오늘 날짜 기준으로 다시)
진행 기록: 스킬 폴더 sourcing_state.json
"""
import json, sys
from datetime import date
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")
STATE = Path(__file__).resolve().parent.parent / "sourcing_state.json"

# 부피가 크고 무거운 제품 — 상품명에 들어 있으면 뺀다(사용자 지정 2026-11-23)
BULKY = ["침대", "매트리스", "소파", "쇼파", "식탁", "옷장", "장롱", "책상", "책장", "서랍장", "수납장", "진열장", "장식장",
         "화장대", "신발장", "냉장고", "세탁기", "건조기", "김치냉장고", "에어컨", "안마의자", "러닝머신", "트레드밀",
         "식기세척기", "의자 세트", "테이블 세트", "캐비닛", "붙박이", "벙커", "2층침대", "평상", "가구", "피아노", "자전거"]

# 1·2단계 공통 카테고리(쿠팡 큰 분류 기준) — 검색어는 그 달 기준으로 아래 표에서 고른다
CATEGORIES = ["생활용품", "주방용품", "가전디지털(소형)", "홈인테리어(소품)", "뷰티", "패션잡화", "스포츠·레저",
              "자동차용품", "반려동물용품", "완구·취미", "문구·오피스", "출산·유아동", "헬스·건강"]

# 달마다 잘 팔리는 계절 검색어(카테고리별). 없는 칸은 계절 상관없는 기본 검색어를 쓴다.
SEASON = {
    "겨울": {  # 11·12·1·2월(한국은 11월부터 추움)
        "생활용품": ["손난로", "핫팩", "보온 물주머니", "문풍지"], "주방용품": ["보온병", "전기 주전자", "보온 도시락"],
        "가전디지털(소형)": ["미니 온풍기", "전기요", "가습기", "전기담요"], "홈인테리어(소품)": ["단열 암막커튼", "뽁뽁이 단열시트", "털 러그"],
        "뷰티": ["핸드크림", "립밤", "보습 크림"], "패션잡화": ["발열장갑", "넥워머", "털 실내화", "귀마개"],
        "스포츠·레저": ["발열조끼", "방한 장갑", "스키 고글"], "자동차용품": ["성에제거기", "열선방석", "앞유리 성에방지커버"],
        "반려동물용품": ["강아지 패딩", "고양이 겨울집", "펫 전기방석"], "완구·취미": ["눈썰매", "크리스마스 트리 장식", "보드게임"],
        "문구·오피스": ["USB 손난로", "책상 발난로", "다이어리"], "출산·유아동": ["유아 방한복", "유모차 방풍커버"],
        "헬스·건강": ["온열 찜질기", "족욕기", "목 온열 마사지기"]},
    "봄": {  # 3·4·5월
        "생활용품": ["미세먼지 마스크", "제습제", "옷 정리함"], "주방용품": ["피크닉 도시락", "텀블러"],
        "가전디지털(소형)": ["공기청정기 필터", "무선 청소기", "보풀제거기"], "홈인테리어(소품)": ["방충망", "커튼"],
        "뷰티": ["선크림", "클렌징 오일"], "패션잡화": ["우산", "봄 모자", "에코백"], "스포츠·레저": ["캠핑 의자", "등산 스틱", "자전거 장갑"],
        "자동차용품": ["차량용 공기청정기", "세차 용품"], "반려동물용품": ["산책 하네스", "강아지 진드기 방지"],
        "완구·취미": ["비눗방울 총", "연날리기"], "문구·오피스": ["신학기 필통", "노트북 거치대"],
        "출산·유아동": ["유아 킥보드", "아기 자외선 차단"], "헬스·건강": ["요가매트", "폼롤러"]},
    "여름": {  # 6·7·8월
        "생활용품": ["모기 퇴치기", "제습제", "쿨 이불"], "주방용품": ["얼음 틀", "아이스 텀블러", "빙수기"],
        "가전디지털(소형)": ["손선풍기", "서큘레이터", "넥밴드 선풍기"], "홈인테리어(소품)": ["암막 블라인드", "창문 단열 필름"],
        "뷰티": ["쿨링 선스틱", "데오드란트"], "패션잡화": ["쿨토시", "양산", "아쿠아슈즈"], "스포츠·레저": ["물놀이 튜브", "방수팩", "캠핑 쿨러"],
        "자동차용품": ["차량용 햇빛가리개", "통풍 시트"], "반려동물용품": ["강아지 쿨매트", "펫 아이스 조끼"],
        "완구·취미": ["물총", "어린이 수영장"], "문구·오피스": ["USB 선풍기", "쿨링 패드"],
        "출산·유아동": ["유아 수영복", "아기 모기장"], "헬스·건강": ["쿨링 마사지기", "냉찜질팩"]},
    "가을": {  # 9·10월
        "생활용품": ["가습기", "제습제", "옷 압축팩"], "주방용품": ["전기 주전자", "에어프라이어 용기"],
        "가전디지털(소형)": ["가습기", "전기요", "보풀제거기"], "홈인테리어(소품)": ["극세사 러그", "문풍지"],
        "뷰티": ["보습 크림", "립밤"], "패션잡화": ["니트 모자", "머플러"], "스포츠·레저": ["등산 장갑", "캠핑 랜턴", "핫팩"],
        "자동차용품": ["차량용 가습기", "와이퍼"], "반려동물용품": ["강아지 옷", "고양이 숨숨집"],
        "완구·취미": ["할로윈 소품", "퍼즐"], "문구·오피스": ["다이어리", "탁상 달력"],
        "출산·유아동": ["유아 내복", "아기 가습기"], "헬스·건강": ["온열 찜질기", "족욕기"]},
}
# 3단계 — 계절 상관없는 욕실·주방·거실 용품(부피 작은 것)
EVERGREEN = {
    "욕실용품": ["욕실 선반", "샤워기 필터", "배수구 거름망", "욕실 미끄럼방지", "칫솔 살균기", "수건 걸이", "변기 클리너"],
    "주방용품": ["싱크대 거름망", "실리콘 주방도구", "밀폐용기", "채칼", "냄비 정리대", "주방 저울", "음식물 쓰레기통"],
    "거실용품": ["멀티탭 정리함", "리모컨 거치대", "무선 청소포", "먼지 제거 롤러", "간접 조명", "코드 정리", "틈새 청소솔"],
}


def season_of(month):
    return {11: "겨울", 12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄", 6: "여름", 7: "여름", 8: "여름"}.get(month, "가을")


def month_add(d, k):
    m = d.month - 1 + k
    return date(d.year + m // 12, m % 12 + 1, 1)


def load():
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    today = date.today()
    st = {"started": today.isoformat(), "phase": 1, "done": {"1": [], "2": [], "3": []},
          "phase1_month": today.month, "phase2_month": month_add(today, 2).month}
    save(st)
    return st


def save(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def plan(st):
    """(단계, 카테고리, 검색어 후보, 설명) — 남은 첫 카테고리."""
    p = st["phase"]
    if p in (1, 2):
        month = st["phase1_month"] if p == 1 else st["phase2_month"]
        sea = season_of(month)
        for c in CATEGORIES:
            if c not in st["done"][str(p)]:
                kws = SEASON[sea].get(c) or EVERGREEN.get(c, [])
                desc = ("최근 1달(%d월) 잘 팔리는 상품" % month) if p == 1 else ("2달 뒤(%d월) 잘 팔릴 상품 — 미리 영상화" % month)
                return p, c, kws, desc + f" · 계절: {sea}"
        return None
    for c, kws in EVERGREEN.items():
        if c not in st["done"]["3"]:
            return 3, c, kws, "계절과 상관없는 생활용품(부피 작은 것만)"
    return None


def advance(st):
    while st["phase"] <= 3 and plan(st) is None:
        st["phase"] += 1
    save(st)


cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
st = load()
if cmd == "reset":
    STATE.unlink(missing_ok=True); st = load(); print("처음부터 다시:", st["started"]); sys.exit(0)
if cmd == "check":
    name = " ".join(sys.argv[2:])
    hit = [w for w in BULKY if w in name]
    if hit:
        print("제외: 부피 크고 무거운 제품(%s) → 다음 순위 상품으로" % ", ".join(hit)); sys.exit(3)
    print("통과"); sys.exit(0)
if cmd in ("done", "skip"):
    c = " ".join(sys.argv[2:])
    p = plan(st)
    if not p:
        sys.exit("모든 단계가 끝났어요")
    st["done"][str(p[0])].append(c or p[1]); advance(st)
    print(("완료" if cmd == "done" else "건너뜀"), c or p[1])
    cmd = "next"
if cmd == "status":
    for k in ("1", "2", "3"):
        total = len(CATEGORIES) if k != "3" else len(EVERGREEN)
        print(f"{k}단계: {len(st['done'][k])}/{total} — {', '.join(st['done'][k]) or '-'}")
    print("지금:", st["phase"] if st["phase"] <= 3 else "모두 끝")
    sys.exit(0)
if cmd == "next":
    p = plan(st)
    if not p:
        print("모든 단계(1·2·3)를 끝냈어요. 새로 시작하려면 reset"); sys.exit(0)
    ph, c, kws, desc = p
    print(f"{ph}단계 · {c} — {desc}")
    print("검색어 후보(판매량순 검색):", ", ".join(kws))
    print("※ 부피 크고 무거운 제품(침대·소파·식탁·옷장 등)은 빼고, 광고 아닌 상위 상품부터")
