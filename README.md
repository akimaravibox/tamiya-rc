# 타미야 RC카 대회 신청정보 조회

## 배포 방법 (GitHub Pages)

### 1단계: GitHub 저장소 생성
1. https://github.com 접속 → 로그인
2. 우측 상단 `+` → `New repository`
3. Repository name: `tamiya-rc` (아무 이름)
4. **Public** 선택 (Pages 무료 사용 조건)
5. `Create repository` 클릭

### 2단계: 파일 업로드
1. 저장소 페이지에서 `Add file` → `Upload files`
2. 아래 파일 전부 업로드:
   - `index.html`
   - `data.json`
   - `fetch_data.py`
   - `.github/workflows/fetch.yml`
3. `Commit changes` 클릭

### 3단계: GitHub Pages 활성화
1. 저장소 → `Settings` → `Pages`
2. Source: `Deploy from a branch`
3. Branch: `main` / `/ (root)` 선택
4. `Save` 클릭
5. 잠시 후 URL 생성됨:
   `https://[내 아이디].github.io/tamiya-rc/`

### 4단계: Actions 권한 설정
1. 저장소 → `Settings` → `Actions` → `General`
2. `Workflow permissions` → `Read and write permissions` 선택
3. `Save` 클릭

### 완료!
- 매 시간 정각에 자동으로 데이터 갱신
- 수동 갱신: `Actions` 탭 → `신청정보 갱신` → `Run workflow`

## 대회 기간 변경
`fetch_data.py` 상단의 날짜 수정:
```python
START_DATE = date(2025, 5, 27)   # 시작일
END_DATE   = date(2025, 6,  7)   # 종료일
```
