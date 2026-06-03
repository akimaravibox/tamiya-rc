"""
타미야 RC카 대회 신청정보 조회 → data.json 저장
GitHub Actions 에서 자동 실행됨
- 평상시: 오늘 날짜만 조회 후 기존 data.json 에 추가/갱신
- 전체 재조회: FULL_REFRESH=true 환경변수 설정 시 시작일부터 전체 조회
"""

import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timezone, timedelta
import json
import time
import os

# ── 설정 ──────────────────────────────────────────────
START_DATE  = date(2026, 5, 18)   # ← 대회 시작일 (고정)
END_DATE    = date(2026, 6, 11)   # ← 대회 종료일
MAX_INDEX   = 300
EMPTY_LIMIT = 200
DELAY_SEC   = 0
MAX_RETRY   = 3
LOOKUP_URL  = "https://tamiya.co.kr/sub/mini_car_challenge_result.php"
OUTPUT_FILE = "data.json"
KST         = timezone(timedelta(hours=9))
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
                "접수번호":   receipt_no,
                "참가자명":   data.get("참가자명", ""),
                "참가클래스": data.get("참가클래스", ""),
            }
        except Exception as e:
            wait = 3 * attempt
            print(f"  [재시도 {attempt}/{MAX_RETRY}] {receipt_no} → {wait}초 대기: {e}", flush=True)
            time.sleep(wait)

    return None


def load_existing() -> dict:
    """기존 data.json 로드. 없으면 빈 구조 반환"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "updated_at":   date.today().isoformat(),
        "total":        0,
        "start_date":   START_DATE.isoformat(),
        "end_date":     date.today().isoformat(),
        "class_count":  {},
        "participants": [],
    }


def fetch_range(start: date, end: date, participants_map: dict) -> int:
    """start ~ end 날짜 범위를 조회해서 participants_map 에 머지. 신규 건수 반환"""
    new_count = 0
    current   = start

    while current <= end:
        print(f"\n[{current}] 조회 중...", flush=True)
        empty_count = 0

        for idx in range(1, MAX_INDEX + 1):
            rno  = make_receipt_no(current, idx)
            info = lookup(rno)

            if info:
                empty_count = 0
                is_new = rno not in participants_map
                participants_map[rno] = info
                print(f"  {'[NEW]' if is_new else '[UPD]'} {rno}  {info['참가자명']}  {info['참가클래스']}", flush=True)
                if is_new:
                    new_count += 1
            else:
                empty_count += 1
                print(f"  . {rno}  (빈 결과 연속 {empty_count}건)", flush=True)
                if empty_count >= EMPTY_LIMIT:
                    print(f"  연속 빈 결과 {EMPTY_LIMIT}건 → 다음 날짜", flush=True)
                    break

            time.sleep(DELAY_SEC)

        current += timedelta(days=1)

    return new_count


def main():
    today        = datetime.now(KST).date()
    full_refresh = os.environ.get("FULL_REFRESH", "false").lower() == "true"

 # 대회 종료일 이후면 조회 안 함  ← 이 부분 추가
    if today > END_DATE:
        print(f"접수 종료. (종료일: {END_DATE})")
        return
    
    # 대회 시작 전이면 조회 불필요
    if today < START_DATE:
        print(f"대회 시작 전입니다. (시작일: {START_DATE})")
        return

    # ── 기존 data.json 로드 ──────────────────────────────
    existing = load_existing()
    participants_map = {
        p["접수번호"]: p for p in existing.get("participants", [])
    }

    if full_refresh:
        # 전체 재조회: 시작일 ~ 오늘
        print(f"전체 재조회 모드: {START_DATE} ~ {today}", flush=True)
        participants_map = {}  # 기존 데이터 초기화 후 전체 새로 조회
        new_count = fetch_range(START_DATE, today, participants_map)
    else:
        # 오늘만 조회
        print(f"오늘 날짜 조회: {today}", flush=True)
        new_count = fetch_range(today, today, participants_map)

    # ── 전체 참가자 정렬 & 집계 ──────────────────────────
    all_participants = sorted(
        participants_map.values(),
        key=lambda x: x["참가클래스"]
    )

    class_count = {}
    for p in all_participants:
        k = p["참가클래스"]
        class_count[k] = class_count.get(k, 0) + 1

    # ── data.json 저장 ────────────────────────────────────
    output = {
        "updated_at":   today.isoformat(),
        "total":        len(all_participants),
        "start_date":   START_DATE.isoformat(),
        "end_date":     today.isoformat(),
        "class_count":  class_count,
        "participants": all_participants,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    mode = "전체 재조회" if full_refresh else "오늘 조회"
    print(f"\n[{mode}] 저장 완료 -> {OUTPUT_FILE}  (전체 {len(all_participants)}명 / 신규 {new_count}명)", flush=True)

if __name__ == "__main__":
    main()
