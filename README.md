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

## 들어오기

사이트를 열면 먼저 **입장 비밀번호**를 묻습니다. 동아리원끼리 나눠 갖는 하나의
비밀번호이고, 이걸 넣어야 시간표가 보입니다. 주소만 아는 사람은 데이터를 받아갈
수 없습니다 — 화면뿐 아니라 서버 요청 자체가 막힙니다.

한 번 넣으면 그 브라우저에 남아 다음부터는 묻지 않습니다. 관리자가 비밀번호를
바꾸면 모두 다시 넣어야 합니다.

관리자는 **입장 설정**에서 첫 화면 문구와 입장 비밀번호를 고칠 수 있습니다.

비밀번호가 셋이라 헷갈리기 쉬우니 정리하면 이렇습니다.

| 비밀번호 | 무엇을 여는가 | 누가 아는가 | 브라우저에 남는가 |
|---|---|---|:---:|
| 입장 | 사이트 자체 | 동아리원 전체가 같은 것 | 남음 |
| 개인 4자리 | 내 일정 고치기 | 본인만 | 안 남음 |
| 관리자 | 전부 고치기 · 입장 설정 | 운영하는 사람 | 안 남음 |

## 쓰는 법

1. **이름 등록** — 본인 이름과 숫자 4자리 비밀번호를 정합니다
2. **내 일정** — 요일·시작·종료·제목을 골라 매주 반복되는 일정을 넣습니다.
   목록은 `수  09:00 ~ 11:00  데이터베이스` 같은 텍스트 한 줄로 보입니다
3. **이름 선택** — 보고 싶은 사람을 여러 명 고르면 요일마다 열이 나뉘어 나란히 보입니다
4. **수정** — 이름을 하나만 고르고 수정 버튼을 누르면 격자를 직접 만질 수 있습니다

수정 중에는 이렇게 씁니다.

- 빈 칸을 **끌면** 그 자리에 점선 상자가 생깁니다. 손을 떼도 남아 있으니 위아래
  끝을 잡아 길이를 고치고, 가운데를 잡아 다른 요일로 옮긴 뒤 **⊕** 를 누르면
  제목을 넣는 폼이 열립니다. 치우려면 ESC 를 누르거나 빈 칸을 한 번 누릅니다
- 이미 있는 일정도 **잡아서 옮깁니다.** `Ctrl`(맥은 `Cmd`)을 누른 채 옮기면
  원본을 두고 하나 더 만듭니다 — 같은 수업이 주 이틀 있을 때 쓰면 편합니다
- 이미 있는 일정과 자리가 겹치면 **빨갛게** 바뀌고 놓이지 않습니다

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
$env:GATE_PASSWORD='club-gate'
.venv/Scripts/python -m uvicorn app.main:create_production_app --factory --reload --port 8000
```

둘 다 없으면 서버가 뜨지 않습니다 — 게이트 없이 배포되는 사고를 막기 위해서입니다.

프론트엔드 (`frontend/`):

```
npm install
npm run dev      # http://localhost:5173 — /api 요청은 8000으로 프록시
```

테스트:

```
cd backend  && .venv/Scripts/python -m pytest    # 176개
cd frontend && npm test                          # 116개
```

## 배포

### Railway

**1. GitHub 에 올립니다** (저장소는 비공개로 두세요)

```
gh repo create 4thIS-schedule-table --private --source=. --remote=origin --push
```

**2. Railway 에서 프로젝트를 만듭니다**

[railway.app](https://railway.app) 에 GitHub 계정으로 로그인 →
**New Project → Deploy from GitHub repo** → 이 저장소 선택.
루트의 `Dockerfile` 을 알아서 찾아 빌드합니다.

**3. Variables 에 둘을 넣습니다**

```
ADMIN_PASSWORD = 충분히 긴 비밀번호
GATE_PASSWORD  = 동아리원에게 나눠 줄 비밀번호
```

둘 중 하나라도 없으면 컨테이너가 시작하지 못하고 재시작을 반복합니다.

**4. 볼륨을 붙입니다 — 이 단계를 빠뜨리면 안 됩니다**

**Settings → Volumes → New Volume**, 마운트 경로 `/data`.
**빠뜨리면 다시 배포할 때마다 등록한 이름과 일정이 전부 사라집니다.**
볼륨은 나중에 붙여도 되지만, 그때까지 쌓인 데이터는 옮겨오지 못합니다.

**5. 주소를 만듭니다**

**Settings → Networking → Generate Domain** →
`무엇무엇.up.railway.app` 주소가 나옵니다. 이걸 동아리원에게 알려주면 됩니다.

**6. 첫 접속 후**

입장 비밀번호를 넣고 들어가서 **입장 설정**에서 첫 화면 문구를 동아리에 맞게
고칩니다. 입장 비밀번호도 여기서 바꿀 수 있고, 이렇게 바꾼 값은 `GATE_PASSWORD`
환경변수보다 우선해 다시 배포해도 유지됩니다.

> `GATE_PASSWORD` 는 **DB 가 비어 있을 때만** 심어집니다. `ADMIN_PASSWORD` 는
> 반대로 부팅할 때마다 덮어씁니다 — 관리자 비밀번호를 잊으면 환경변수를 바꿔
> 되찾을 수 있게 하려는 것입니다.

### 직접 돌리기

```
docker build -t club-schedule .
docker run -d -p 8000:8000 \
  -e ADMIN_PASSWORD="충분히 긴 비밀번호" \
  -e GATE_PASSWORD="동아리 입장 비밀번호" \
  -v club-data:/data --restart unless-stopped club-schedule
```

> **Vercel 은 쓸 수 없습니다.** Python 함수가 서버리스로 돌아 파일시스템이 읽기
> 전용이고 요청마다 인스턴스가 새로 뜹니다. SQLite 에 쓴 데이터가 남지 않습니다.

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `ADMIN_PASSWORD` | (필수) | 관리자 비밀번호. 부팅할 때마다 이 값으로 덮어씁니다 |
| `GATE_PASSWORD` | (필수) | 입장 비밀번호. **DB 가 비어 있을 때만** 심습니다 |
| `DB_PATH` | `/data/schedule.db` | SQLite 파일 경로 |
| `FRONTEND_DIST` | `/srv/frontend/dist` | 빌드된 프론트 경로 |
| `PORT` | `8000` | 들을 포트. Railway·Fly 는 자동으로 넣어 줍니다 |

uvicorn 워커는 **1개**여야 합니다. 비밀번호 시도 제한과 입장 검증 기억이 프로세스
메모리에 있어서, 워커가 여러 개면 제한이 워커 수만큼 느슨해집니다.

## 구조

```
backend/app/
  constants.py   슬롯·팔레트·제한값. 다른 모듈은 숫자를 직접 쓰지 않는다
  timeslot.py    슬롯 정수 <-> "HH:MM" 변환, 겹침 판정
  db.py          SQLite 스키마와 커넥션 (날짜 컬럼 없음)
  auth.py        해시, 시도 제한, 요청 주체 판정, 권한 가드
  gate.py        입장 비밀번호·첫 화면 문구, 통과한 비밀번호 기억
  config.py      환경변수 읽기 (없으면 뜨지 않는다)
  schemas.py     Pydantic 입출력 모델
  routers/       board · auth · gate · categories · members · schedules
frontend/src/
  utils/timeSlot.ts    슬롯 <-> 시간 변환
  utils/gridLayout.ts  격자 열 구성과 블록 배치 (순수 함수 — 브라우저 없이 검증)
  utils/draftBox.ts    초안의 크기·자리 규칙과 겹침 판정 (경계, 최소 길이)
  stores/board.ts      Pinia 상태
  components/          격자, 멤버 패널, 다이얼로그들
```

시간을 30분 슬롯 정수(0=06:00 ~ 36=24:00)로 다뤄서, 겹침 검사는 정수 비교
한 줄이고 격자 배치는 CSS Grid의 행 번호로 바로 쓰입니다.

## 설계 문서

- 스펙: `docs/superpowers/specs/2026-07-31-club-weekly-schedule-design.md`
- 구현 계획: `docs/superpowers/plans/2026-07-31-club-weekly-schedule.md`

