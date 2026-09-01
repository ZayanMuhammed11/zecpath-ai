# Zecpath AI

AI-powered hiring intelligence platform for Quality Engineering (QE) roles across three real industry sectors: automotive manufacturing, food safety, and pharmaceutical quality.



## Overview

Zecpath covers the full hiring pipeline through independent, deterministic, tested AI modules:

- **ATS Engine** — resume parsing, QE-domain skill/experience/education scoring
- **Screening AI** — candidate eligibility, screening question bank, transcript scoring
- **HR Interview AI** — communication, confidence, and behavioral scoring
- **Technical Interview AI** — sector-specific technical evaluation (automotive / food safety / pharmaceutical)
- **Machine Test AI** — practical task scoring
- **Visual Behavior AI** / **Integrity AI** — engagement and risk signal scoring (caller-supplied signal inputs)
- **Decision AI** — cross-round score aggregation with proportional weight redistribution
- **Final Decision AI** — risk-adjusted final recommendation
- **Hiring Report AI** — consolidated recruiter-facing report
- **Governance AI** — RBAC and audit-log entry shaping

All scoring is deterministic, rule-based, and explainable — no black-box ML scoring anywhere on the platform. The only LLM usage is one-time structured extraction (resume/JD parsing via Groq); all downstream computation is deterministic Python.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12.7 |
| API Framework | FastAPI |
| Data Validation | Pydantic v2 |
| Task Queue | Redis + RQ (Docker) |
| LLM (one-time extraction only) | Groq `llama-3.3-70b-versatile` |
| Semantic Scoring | scikit-learn TF-IDF cosine similarity |
| PDF Parsing | pdfplumber |
| DOCX Parsing | python-docx |
| Testing | pytest |
| OS / Terminal | Windows 11 / PowerShell |

## Project Structure

```
zecpath-ai/
├── ats_engine/           # JD parsing, skill extraction, ranking, fairness engine
├── parsers/               # Resume text extraction, section classification, education parsing
├── scoring/                # ATS scoring engine, semantic scorer, role weights
├── screening_ai/          # Eligibility, question bank, transcript, screening scoring
├── interview_ai/          # HR interview: communication, confidence, aptitude, summary
├── technical_ai/           # Technical interview question bank + scoring
├── machine_test_ai/       # Machine test scoring (generic software-engineering track)
├── visual_behavior_ai/    # Visual engagement signal scoring
├── integrity_ai/          # Malpractice/integrity risk scoring
├── decision_ai/            # Cross-round score aggregation (5 rounds)
├── final_decision_ai/     # Risk-adjusted final recommendation
├── hiring_report_ai/      # Consolidated hiring intelligence report
├── governance_ai/         # RBAC + audit log entry shaping
├── api/                    # Redis client, request/response models
├── routers/                 # FastAPI routers (ATS, eligibility, screening)
├── worker/                  # RQ task handlers
├── utils/                   # Pydantic schemas, logger, LLM client
├── config/                  # Environment-based settings
├── data/                    # Sample resumes, JDs, question banks, demo datasets
├── tests/                   # pytest suite + standalone simulation scripts
├── main.py                  # FastAPI app entry point
└── requirements.txt
```

## Setup Instructions

1. Clone the repository:
   ```powershell
   git clone https://github.com/ZayanMuhammed11/zecpath-ai
   cd zecpath-ai
   ```

2. Create and activate the virtual environment:
   ```powershell
   python -m venv zecc
   zecc\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure environment variables — create a `.env` file with:
   ```
   GROQ_API_KEY=your_key_here
   REDIS_URL=redis://localhost:6379
   ```

5. Start Redis (Docker Desktop must be running):
   ```powershell
   docker start zecpath-redis
   ```

## Running the System

**Terminal 1 — API server:**
```powershell
zecc\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — background worker:**
```powershell
zecc\Scripts\Activate.ps1
rq worker --worker-class rq.SimpleWorker ats_queue
```

Swagger UI: `http://localhost:8000/docs`

## Running Tests

```powershell
pytest
```

Expected: **461 passed**, zero regressions.

## Running Demo Simulations

The platform's 9 API-less modules (interview_ai, technical_ai, machine_test_ai, visual_behavior_ai, integrity_ai, decision_ai, final_decision_ai, hiring_report_ai, governance_ai) are validated via standalone simulation scripts rather than a live API — see "Known Limitations" below.

```powershell
python -m tests.simulate_screening
python -m tests.simulate_hr_interview
python -m tests.simulate_full_candidate_journey
python -m tests.simulate_full_system_day56          # full 9-module chain, structural edge cases
python -m tests.simulate_demo_dataset_day63          # 3 tiered-quality QE candidates, real input+output JSON
```

## Live API Endpoints (Real, Implemented)

9 endpoints across 3 module groups:

| Group | Endpoints |
|---|---|
| ATS | `POST /resume/upload`, `POST /resume/parse`, `GET /jobs/status/{job_id}`, `POST /ats/score`, `POST /ats/shortlist` |
| Eligibility | `POST /eligibility/evaluate`, `POST /eligibility/evaluate-batch`, `GET /eligibility/result/{candidate_id}/{job_id}` |
| Screening | `POST /screening/run` |



## Author

Zayan Muhammed — AI Developer Intern, Zecser Business LLP
