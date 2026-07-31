# 동아리 주간 시간표

동아리원이 각자 접속해 매주 반복되는 고정 일정(수업·알바·강의)을 등록하고,
여러 명의 시간표를 엑셀형 격자에 나란히 놓고 비교하는 웹 앱입니다.

날짜 개념이 없습니다. 다루는 정보는 **"어느 요일 몇 시부터 몇 시까지 무슨 일정"** 뿐입니다.

```
         │      월      │      화      │   ... 가로 스크롤 →
  시간   │철수│영희│민수│철수│영희│민수│
  09:00  │수업│    │알바│    │강의│    │
  09:30  │ ↕  │    │ ↕  │    │ ↕  │수업│   ← 세로 06:00~24:00, 30분 36줄
  10:00  │    │강의│ ↕  │    │    │ ↕  │
```

여러 칸에 걸친 일정은 **세로로 긴 블록 하나**로 그려지고 제목은 그 안에 한 번만 들어갑니다.

## 쓰는 법

1. **이름 등록** — 본인 이름과 숫자 4자리 비밀번호를 정합니다
2. **내 일정** — 요일·시작·종료·제목을 골라 매주 반복되는 일정을 넣습니다.
   목록은 `수  09:00 ~ 11:00  데이터베이스` 같은 텍스트 한 줄로 보입니다
3. **이름 선택** — 보고 싶은 사람을 여러 명 고르면 요일마다 열이 나뉘어 나란히 보입니다

비밀번호는 본인 일정을 지키기 위한 것입니다. 관리자 비밀번호로는 모든 일정을
고칠 수 있고, **카테고리(학년) 관리와 이름 순서·소속 변경은 관리자만** 할 수 있습니다.

| 동작 | 익명 | 본인 | 관리자 |
|---|:---:|:---:|:---:|
| 시간표 조회 | O | O | O |
| 이름 등록 | O | O | O |
| 본인 일정 추가·수정·삭제 | X | O | O |
| 본인 이름·비밀번호 변경, 계정 삭제 | X | O | O |
| 타인의 것 전부 | X | X | O |
| 이름 순서·소속 드래그 | X | X | O |
| 카테고리 추가·수정·삭제·순서 | X | X | O |

## 개발

백엔드 (`backend/`):

```
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
$env:ADMIN_PASSWORD='admin-secret'
.venv/Scripts/python -m uvicorn app.main:create_production_app --factory --reload --port 8000
```

프론트엔드 (`frontend/`):

```
npm install
npm run dev      # http://localhost:5173 — /api 요청은 8000으로 프록시
```

테스트:

```
cd backend  && .venv/Scripts/python -m pytest    # 146개
cd frontend && npm test                          # 51개
```

## 배포

```
docker build -t club-schedule .
docker run -d -p 8000:8000 -e ADMIN_PASSWORD="충분히 긴 비밀번호" \
  -v club-data:/data --restart unless-stopped club-schedule
```

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `ADMIN_PASSWORD` | (필수) | 관리자 비밀번호. 길이 제한 없음, 8자 이상 권장 |
| `DB_PATH` | `/data/schedule.db` | SQLite 파일 경로 |
| `FRONTEND_DIST` | `/srv/frontend/dist` | 빌드된 프론트 경로 |

uvicorn 워커는 **1개**여야 합니다. 비밀번호 시도 제한 카운터가 프로세스 메모리에
있어서, 워커가 여러 개면 제한이 워커 수만큼 느슨해집니다.

## 구조

```
backend/app/
  constants.py   슬롯·팔레트·제한값. 다른 모듈은 숫자를 직접 쓰지 않는다
  timeslot.py    슬롯 정수 <-> "HH:MM" 변환, 겹침 판정
  db.py          SQLite 스키마와 커넥션 (날짜 컬럼 없음)
  auth.py        해시, 시도 제한, 요청 주체 판정, 권한 가드
  schemas.py     Pydantic 입출력 모델
  routers/       board · auth · categories · members · schedules
frontend/src/
  utils/timeSlot.ts    슬롯 <-> 시간 변환
  utils/gridLayout.ts  격자 열 구성과 블록 배치 (순수 함수 — 브라우저 없이 검증)
  stores/board.ts      Pinia 상태
  components/          격자, 멤버 패널, 다이얼로그들
```

시간을 30분 슬롯 정수(0=06:00 ~ 36=24:00)로 다뤄서, 겹침 검사는 정수 비교
한 줄이고 격자 배치는 CSS Grid의 행 번호로 바로 쓰입니다.

## 설계 문서

- 스펙: `docs/superpowers/specs/2026-07-31-club-weekly-schedule-design.md`
- 구현 계획: `docs/superpowers/plans/2026-07-31-club-weekly-schedule.md`
