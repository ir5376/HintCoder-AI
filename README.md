# Nextep MVP

Nextep is a provider-independent AI Learning OS. It turns coding platforms, imported problems, PDF content, and user notes into learning items that can move through one learning loop: input, learn, review, and remember.

The MVP currently supports Coding and Information Processing Engineer content through reusable learning engine components.

## Run

```bash
streamlit run app.py
```

## Test

```bash
pytest
```

## Current Modules

- Coding
- Information Processing Engineer
- Provider-based problem import
- Problem library with category and difficulty filters
- Problem detail page
- Learning Experience home UI
- Sidebar navigation
- SQLite + SQLAlchemy database initialization
- Starter code display
- Seed problem samples

## Learning OS Capabilities

- Learning Mode and Exam Mode
- AI Coaching
- Progressive hints
- Learning Context before hint generation
- XP, missions, review queue, reflection, thought profile, and learning DNA
- Hint analytics
- Learning history
- Review scheduling

## Provider And Import Capabilities

- Provider Hub architecture
- URL import
- Provider-independent import service
- LeetCode provider adapter
- Programmers provider adapter
- Baekjoon provider adapter
- Custom provider adapter
- External Problem Mode for browser extension query parameters
- Original provider metadata preserved on imported problems

## Frontend Capabilities

- Home page
- Sidebar
- Problem List page
- Problem Detail page
- Learning Experience UI
- In-app navigation between Home, Problem Library, Problem Detail, Learning Context, and Reflection

## Backend Capabilities

- FastAPI import API
- SQLite persistence
- SQLAlchemy models and repositories
- OpenAI/Gemini-backed hint integration when credentials are configured
- Provider-independent Learning Item model
- Learning history, assessment, reflection, review queue, and weakness analysis models

## MVP Notes

- Coding remains the first complete content module.
- Information Processing Engineer exists as a demonstration non-coding module.
- Provider adapters normalize external platform data before it enters the Learning Engine.
- The Learning Engine should not depend on LeetCode, Programmers, PDF, or Notes-specific logic.
