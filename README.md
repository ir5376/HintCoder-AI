# HintCode MVP

Python 기반 AI 코딩 학습 앱의 1단계 MVP입니다.

## 설치

1. Python 3.12 이상을 설치합니다.
2. 가상 환경을 만듭니다.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. `.env.example`을 복사하여 `.env`로 생성합니다.

```bash
copy .env.example .env
```

## 실행

```bash
streamlit run app.py
```

## 테스트

```bash
pytest
```

## 기능

- SQLite + SQLAlchemy 기반 DB 자동 초기화
- 문제 목록 / 카테고리 및 난이도 필터
- 문제 상세 보기
- starter_code 표시
- 문제 샘플 10개 제공

## AI 힌트 백엔드

- 플랫폼 독립적인 문제 컨텍스트 구조 지원: source_platform, source_url, external_problem_id, title, description, constraints, examples, difficulty, programming_language, student_code, execution_result, hint_level
- OpenAI Responses API 기반 힌트 생성
- OPENAI_API_KEY 환경 변수만 사용
- OpenAI 실패 또는 키 부재 시 영어 fallback 힌트 제공
- 힌트 히스토리 저장 및 테스트 커버

### 환경 변수

```bash
copy .env.example .env
```

`.env`에서 `OPENAI_API_KEY`를 설정하세요.

## 미구현

- 사용자 코드 실행 및 채점
- 로그인 / 관리자 페이지
