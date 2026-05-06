# zecpath-ai
AI microservices for Zecpath autonomous hiring platform
# Zecpath AI System

AI microservices for the Zecpath autonomous hiring platform.

## Project Structure

| Folder | Purpose |
|---|---|
| `data/` | Sample resumes and test data |
| `parsers/` | PDF and document parsing logic |
| `ats_engine/` | ATS AI Service - resume scoring and shortlisting |
| `screening_ai/` | Screening AI Service - voice call and conversation |
| `interview_ai/` | Interview Intelligence - HR and Technical interview AI |
| `scoring/` | Decision and Scoring Service - final aggregation |
| `utils/` | Shared utilities - logger, LLM client, Pydantic schemas |
| `config/` | Settings, API keys, model configuration |
| `tests/` | Unit tests for all modules |

## Setup

1. Clone the repo and navigate into it
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your API keys
6. Run tests: `pytest tests/ -v`

## Code Standards

- Every file must have a module-level docstring explaining what it does
- Every function must have a docstring
- Use type hints on all function parameters and return values
- Use `get_logger(__name__)` from `utils.logger` for all logging
- Never hardcode API keys - always use `config/settings.py`
- Pydantic models for all data structures - defined in `utils/schemas.py`

## Environment

- Python 3.11
- LLM: Groq API (llama-3.3-70b-versatile)
- Database: PostgreSQL
- Queue: Redis + Celery
- Framework: FastAPI + LangGraph