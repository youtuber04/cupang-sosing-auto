// 쿠팡 검색 결과(판매량순) 화면에서 상품 목록을 뽑는다. 앱 안 브라우저의 JavaScript 실행 도구로 실행한다.
// 먼저 이 주소로 이동: https://www.coupang.com/np/search?q=<검색어>&sorter=saleCountDesc
// 결과: 위에서부터 순서대로 [{순위, 광고, 상품번호, 주소, 상품명, 가격, 리뷰수, 대표사진}] — 광고 아닌 첫 번째가 1위 상품
(() => {
  const body = document.body.innerText;
  if (/Access Denied|접근이 거부|사용권한이 제한|사용권한이 없습니다|Pardon|보안 문자|captcha/i.test(body)) return '차단됨: 사람이 직접 확인해야 함(자동으로 풀지 않음)';
  const num = (s) => { const m = String(s || '').replace(/,/g, '').match(/\d+/); return m ? Number(m[0]) : null; };
  const seen = new Set(); const out = [];
  for (const a of document.querySelectorAll('a[href*="/vp/products/"]')) {
    const m = a.href.match(/products\/(\d+)/);
    if (!m || seen.has(m[1])) continue;
    seen.add(m[1]);
    const li = a.closest('li') || a;
    const text = (li.innerText || '').replace(/\s+/g, ' ').trim();
    const ad = /_ads|adsplatform|adType=/.test(a.href) || /광고/.test(text) || !!li.querySelector('[class*="AdMark" i], [class*="ad-badge" i]');
    const img = li.querySelector('img');
    const priceEl = li.querySelector('[class*="price-value"], [class*="Price_priceValue"], strong[class*="price" i]');
    const rateEl = li.querySelector('[class*="ProductRating_productRating"], [class*="rating-total-count"]');
    out.push({
      순위: out.length + 1, 광고: ad, 상품번호: m[1], 주소: a.href.split('#')[0],
      상품명: (img && img.alt) || text.slice(0, 80),
      가격: priceEl ? num(priceEl.innerText) : null,
      리뷰수: rateEl ? num(rateEl.innerText) : null,
      대표사진: img ? (img.getAttribute('src') || img.dataset.src || '') : '',
    });
  }
  const first = out.find((x) => !x.광고) || null;
  return JSON.stringify({ 광고아닌1위: first, 목록: out.slice(0, 15) }, null, 1);
})()
