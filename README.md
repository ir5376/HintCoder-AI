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

## 미구현

- 사용자 코드 실행 및 채점
- OpenAI API 호출
- 로그인 / 관리자 페이지
