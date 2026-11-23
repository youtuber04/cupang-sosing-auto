"""판매량순 화면에서 고른 쿠팡 1위 상품을 작업폴더에 저장하고 간편링크(딥링크 API)를 만든다. 검색 API 는 쓰지 않는다.
사용(스킬 폴더에서):
  python scripts/coupang_browser_pick.py <작업폴더> <검색어> <상품주소> <상품명> <대표사진주소> [가격]
만드는 파일: <작업폴더>/ref/쿠팡상품선택.json, ref/쿠팡간편링크.json, 쿠팡대표사진.jpg
쿠팡 API 가 막혀 있으면 NOLINK=1 로 실행해 상품만 저장하고, 풀린 뒤 NOLINK 없이 다시 실행한다.
"""
import json, os, re, sys, urllib.request
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coupang_api  # noqa: E402

if len(sys.argv) < 6:
    sys.exit(__doc__)
W, kw, url, name, img = sys.argv[1:6]
price = sys.argv[6] if len(sys.argv) > 6 else ""
W = Path(W)
m = re.search(r"products/(\d+)", url)
if not m:
    sys.exit("상품주소에 /vp/products/<번호> 가 없어요")
pid = m.group(1)
q = dict(re.findall(r"[?&](itemId|vendorItemId)=(\d+)", url))
clean = f"https://www.coupang.com/vp/products/{pid}" + (
    f"?itemId={q['itemId']}&vendorItemId={q.get('vendorItemId', '')}" if q.get("itemId") else "")

(W / "ref").mkdir(parents=True, exist_ok=True)
pick = {"query": kw, "source": "쿠팡 판매량순 검색 · 광고 아닌 1위(브라우저)", "picked": {
    "rank": 1, "ad": False, "name": name, "price": price, "productId": pid,
    "itemId": q.get("itemId", ""), "vendorItemId": q.get("vendorItemId", ""), "url": clean}}
(W / "ref/쿠팡상품선택.json").write_text(json.dumps(pick, ensure_ascii=False, indent=1), encoding="utf-8")

if os.environ.get("NOLINK"):
    link, why = "", "보류(NOLINK) — 나중에 NOLINK 없이 다시 실행"
else:
    link, why = coupang_api.deeplink_one(clean)
(W / "ref/쿠팡간편링크.json").write_text(json.dumps(
    {"link": link, "step": "딥링크 API(검색 API 안 씀)", "from_url": clean, "error": why},
    ensure_ascii=False, indent=1), encoding="utf-8")
print("간편링크:", link or ("없음 · " + why))

if img:
    if img.startswith("//"):
        img = "https:" + img
    img = re.sub(r"/thumbnails/remote/\d+x\d+[^/]*/", "/thumbnails/remote/1000x1000ex/", img)
    req = urllib.request.Request(img, headers={"user-agent": "Mozilla/5.0", "referer": "https://www.coupang.com/"})
    (W / "쿠팡대표사진.jpg").write_bytes(urllib.request.urlopen(req, timeout=30).read())
    print("대표사진:", W / "쿠팡대표사진.jpg")
