# HintCode

HintCode is an AI-powered learning platform that helps students study previous exam questions more efficiently.

Users can upload PDF question sets, solve problems, receive AI-generated hints, check their answers, and review explanations in one place.

## Installation

1. install Python 3.12 .
2. create virtual environment.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

copy .env.example .env

```bash
copy .env.example .env
```

## Running

```bash
streamlit run app.py
```

## testing

```bash
pytest
```

## Features

- Upload previous exam questions through PDF
- Automatically extract questions
- AI-generated progressive hints
- Answer checking
- Solution explanations
- Question inventory with category and difficulty filters

## Architecture
PDF Upload
        │
        ▼
Question Extraction
        │
        ▼
Question Database
        │
        ▼
Answer Submission
        │
        ▼
Grading
        │
        ▼
AI Hint
        │
        ▼
Explanation

## Future Work

- Similar Problem Generation
- Quiz Mode
- Personalized Review
- Memory Cards
- Gamification (Attendance & Ranking)

## How Codex Helped

We used Codex throughout development to

- build backend features
- debug errors
- improve project architecture
- implement UI integration
- speed up development

## GPT-5.6 Integration

GPT-5.6 was used throughout the development process to help design the system architecture, improve prompts, debug the application, and accelerate implementation.
