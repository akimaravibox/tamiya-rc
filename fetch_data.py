"""
타미야 RC카 대회 신청정보 조회 → data.json 저장
GitHub Actions 에서 자동 실행됨
"""

import requests
from bs4 import BeautifulSoup
from datetime import date
import json
import time
import sys

# ── 설정 ──────────────────────────────────────────────
START_DATE  = date(2026, 3, 21)   # ← 대회 시작일
END_DATE    = date.today()    # ← 대회 종료일
MAX_INDEX   = 50
EMPTY_LIMIT = 20
DELAY_SEC   = 0
MAX_RETRY   = 3
LOOKUP_URL  = "https://tamiya.co.kr/sub/mini_car_challenge_result.php"
OUTPUT_FILE = "data.json"
# ─────────────────────────────────────────────────────

NO_DATA_KEYWORDS = ["신청정보가 없습니다", "조회된 내역이 없습니다", "결과가 없습니다"]

def make_receipt_no(d: date, idx: int) -> str:
    return f"{d.strftime('%y%m%d')}{idx:04d}"

def lookup(receipt_no: str):
    payload = {
        "board_id":  "",
        "category":  "rc",
        "user_view": "2",
        "part_num":  receipt_no,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer":    "https://tamiya.co.kr/sub/mini_car_challenge_lookup.php?category=rc",
        "Connection": "close",
    }

    for attempt in range(1, MAX_RETRY + 1):
        try:
            s = requests.Session()
            r = s.post(LOOKUP_URL, data=payload, headers=headers, timeout=15)
            r.raise_for_status()
            html = r.text

            if any(kw in html for kw in NO_DATA_KEYWORDS):
                return None

            soup = BeautifulSoup(html, "html.parser")
            box  = soup.find("div", class_="challenger_search_result")
            if not box:
                return None

            data = {}
            for wrap in box.find_all("div", class_="wrap"):
                title = wrap.find("div", class_="title")
                value = wrap.find("div", class_="result_data")
                if title and value:
                    data[title.get_text(strip=True)] = value.get_text(strip=True)

            if not data.get("참가자명"):
                return None

            return {
                "접수번호":  receipt_no,
                "참가자명":  data.get("참가자명", ""),
                "참가클래스": data.get("참가클래스", ""),
            }
        except Exception as e:
            wait = 3 * attempt
            print(f"  [재시도 {attempt}/{MAX_RETRY}] {receipt_no} → {wait}초 대기: {e}")
            time.sleep(wait)

    return None


def main():
    results      = []
    total        = 0
    current      = START_DATE

    print(f"조회 기간: {START_DATE} ~ {END_DATE}")

    while current <= END_DATE:
        print(f"\n[{current}] 조회 중...")
        empty_count = 0

        for idx in range(1, MAX_INDEX + 1):
            rno  = make_receipt_no(current, idx)
            info = lookup(rno)
            total += 1

            if info:
                empty_count = 0
                print(f"  ✔ {rno}  {info['참가자명']}  {info['참가클래스']}")
                results.append(info)
            else:
                empty_count += 1
                if empty_count >= EMPTY_LIMIT:
                    print(f"  연속 빈 결과 {EMPTY_LIMIT}건 → 다음 날짜")
                    break

            time.sleep(DELAY_SEC)

        from datetime import timedelta
        current += timedelta(days=1)

    # 클래스별 정렬
    results.sort(key=lambda x: x["참가클래스"])

    # 클래스별 집계
    class_count = {}
    for r in results:
        k = r["참가클래스"]
        class_count[k] = class_count.get(k, 0) + 1

    # data.json 저장
    output = {
        "updated_at":  date.today().isoformat(),
        "total":       len(results),
        "start_date":  START_DATE.isoformat(),
        "end_date":    END_DATE.isoformat(),
        "class_count": class_count,
        "participants": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 저장 완료 → {OUTPUT_FILE}  ({len(results)}명)")

if __name__ == "__main__":
    main()
