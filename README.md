## Groww Play Store Review Pulse

This project turns recent Groww Play Store reviews into a weekly one page pulse using Groq, then drafts an email with the note.

**Deployment:** Frontend (Vercel) + Backend (Railway). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for steps to deploy the frontend and connect it to the backend.

Phase 1 is implemented:

- Config loaded from environment via `src/config.py`.
- Reusable Groq client wrapper in `src/llm/groq_client.py`.
- PII scrubber utilities in `src/utils/pii_scrubber.py`.
- Basic tests in `tests/` for the Groq client and PII scrubber.

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest
```

