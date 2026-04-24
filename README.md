# 혈당 관리 식단 어시스턴트

위 소매 절제술(Sleeve Gastrectomy) 후 혈당 관리가 필요한 환자를 위한 AI 기반 식단 추천 웹 애플리케이션입니다.  
보유 식재료를 등록하면 AI가 의료 조건에 맞는 3끼 식단과 예산별 구매 목록을 추천합니다.

---

## 주요 기능

| 탭 | 기능 |
|----|------|
| 📦 식재료 | 보유 식재료 등록 · 수량 · 유통기한 관리 |
| 🍽️ 식단 | AI 3끼 식단 자동 생성 · 기록 저장 |
| 📅 기록 | 날짜별 식단 이력 조회 |
| 💰 예산 | 예산 입력 → AI 구매 추천 → 즉시 식재료 추가 |
| ⚙️ 설정 | LLM 제공자 · API 키 · 추론 모드 설정 |

### 의료 조건 (프롬프트 자동 적용)

- **식사량**: 1회 100~150ml (위 절제 후 용량 감소)
- **탄수화물**: 1끼 15g 이하, GI 55 이하 저GI 식품만 허용
- **우선순위**: 단백질 → 채소 → 저GI 탄수화물

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| DB | SQLite (Docker volume으로 영속화) |
| Frontend | Vanilla JS + Tailwind CSS (CDN) |
| AI 클라이언트 | httpx — Ollama / OpenAI / Anthropic 통합 |
| 배포 | Docker Compose |

---

## 빠른 시작

### Docker (권장)

```bash
# Docker Engine 설치 (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 재로그인 필요

# 클론 후 실행
git clone <repo-url> && cd diet2
chmod +x setup.sh && ./setup.sh
```

출력된 `http://<IP>:<포트>` 로 로컬 네트워크 내 모든 기기에서 접속 가능합니다.

### 포트 변경

`docker-compose.yml`에서 왼쪽 포트를 수정 후 재시작:

```yaml
ports:
  - "80:8000"   # 80번 포트로 서비스
```

```bash
docker compose up -d
```

### 로컬 개발

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data && chmod +x run.sh && ./run.sh
```

---

## LLM 설정

앱 실행 후 **⚙️ 설정** 탭에서 설정합니다. 설정은 DB에 저장되어 재시작 후에도 유지됩니다.

### 지원 제공자

| 제공자 | Base URL | API 형식 | 모델 예시 |
|--------|----------|---------|-----------|
| Ollama | `https://ollama.com` | ollama | llama3.2 |
| OpenAI | `https://api.openai.com` | openai | gpt-4o, o4-mini |
| Anthropic | `https://api.anthropic.com` | anthropic | claude-sonnet-4-6 |
| Mistral | `https://api.mistral.ai` | openai | mistral-large-latest |
| OpenRouter | `https://openrouter.ai/api` | openai | anthropic/claude-3.5-sonnet |
| Custom | 직접 입력 | 선택 | 직접 입력 |

### 추론 모드 (Thinking)

| 모드 | 동작 | 지원 |
|------|------|------|
| 없음 | 기본 응답 | 전체 |
| Chain-of-Thought | 시스템 프롬프트에 단계적 추론 지시 추가 | 전체 |
| Native Think ✦ | `think:true` / Extended Thinking API | Ollama, Anthropic |

> Anthropic Extended Thinking 사용 시 `thinking_budget` (토큰 수)를 함께 설정하세요.

---

## 로그 레벨

`docker-compose.yml`의 `LOG_LEVEL` 환경변수로 제어합니다.

```yaml
environment:
  - LOG_LEVEL=INFO   # INFO | DEBUG | TRACE
```

| 레벨 | 출력 내용 |
|------|---------|
| `INFO` | 요청/완료 요약, 소요시간 (기본값) |
| `DEBUG` | 프롬프트(500자), 파싱 응답, DB 조회 건수 |
| `TRACE` | 전체 페이로드, 원시 응답(2000자), 헤더(API 키 마스킹) |

```bash
docker compose logs -f              # 실시간 로그
docker compose logs --tail 100      # 최근 100줄
```

---

## 프로젝트 구조

```
diet2/
├── backend/
│   ├── main.py              # FastAPI 앱 진입점, 라우터 등록
│   ├── database.py          # SQLAlchemy ORM 테이블 정의 + DB 초기화
│   ├── models.py            # Pydantic v2 요청/응답 모델
│   ├── ai_client.py         # 다중 LLM 통합 클라이언트 (Ollama/OpenAI/Anthropic)
│   ├── prompt_builder.py    # 식단·구매 추천 프롬프트 생성
│   ├── logger.py            # 커스텀 로깅 (TRACE 레벨 포함)
│   └── routers/
│       ├── ingredients.py   # 식재료 CRUD
│       ├── meal.py          # AI 식단 생성 + 기록
│       ├── budget.py        # AI 구매 추천 + 기록
│       └── settings.py      # LLM 설정 조회/저장/테스트
├── frontend/
│   └── index.html           # SPA (탭 네비게이션, Tailwind CSS)
├── data/                    # SQLite DB 파일 (Docker volume 마운트)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env                     # 로컬 개발용 환경변수
├── setup.sh                 # Linux 배포 스크립트
└── run.sh                   # 로컬 개발 실행 스크립트
```

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/ingredients` | 식재료 목록 조회 |
| POST | `/api/ingredients` | 식재료 추가 |
| DELETE | `/api/ingredients/{id}` | 식재료 삭제 |
| POST | `/api/meal/generate` | AI 식단 생성 |
| GET | `/api/meal/history` | 식단 기록 조회 |
| POST | `/api/meal/history` | 식단 기록 저장 (날짜 중복 시 덮어쓰기) |
| POST | `/api/budget/recommend` | AI 구매 추천 |
| GET | `/api/budget/weekly` | 이번 주 구매 기록 |
| POST | `/api/budget/purchase` | 구매 기록 추가 |
| DELETE | `/api/budget/{id}` | 구매 기록 삭제 |
| GET | `/api/settings` | LLM 설정 조회 |
| PUT | `/api/settings` | LLM 설정 저장 |
| POST | `/api/settings/test` | API 연결 테스트 |
| GET | `/health` | 헬스체크 |

대화형 API 문서: `http://<host>/docs`

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./data/diet.db` | SQLite DB 경로 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 (TRACE / DEBUG / INFO) |

---

## 주의사항

- API 키는 DB에 평문 저장됩니다. 외부 공개 서버에는 배포하지 마세요.
- `data/` 디렉터리는 `.dockerignore`로 이미지에서 제외되며 Docker volume으로 관리됩니다.
- Ollama Cloud의 일부 모델은 유료 구독이 필요합니다 (`https://ollama.com/upgrade`).
