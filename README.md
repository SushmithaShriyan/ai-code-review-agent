# AI Code Review Agent

An AI agent that watches your GitHub pull requests, reviews the diff for
security, code quality, and performance issues, and posts inline comments
automatically — plus a dashboard to see review history and stats.

## Why this project

Most portfolio AI projects are a RAG chatbot over a PDF. This one is
different on purpose: it's an **agent that takes real actions** (reading a
diff, deciding what's wrong, writing back to GitHub) instead of just
answering questions, and it's a **developer tool**, so it's legible to both
full-stack and AI hiring managers.

## Architecture

```
GitHub PR opened/updated
        │
        ▼
  Webhook (signed) ──▶ FastAPI /webhook/github
                              │
                    1. Verify signature
                    2. Fetch PR diff (GitHub API)
                    3. Run AI agent on diff → structured JSON
                    4. Post inline comments (GitHub API)
                    5. Post summary comment
                    6. Save review to MongoDB
                              │
                              ▼
                      React Dashboard ◀── GET /reviews, /reviews/stats
```

**Backend:** FastAPI (Python) — chosen because it's async end-to-end, has
built-in request validation via Pydantic, and is the natural home for the
OpenAI SDK / LangChain-style AI code.

**Agent:** A single-shot LLM call per PR, forced into structured JSON output
(no free-text parsing, no regex). See `backend/app/agent.py` — this is the
file to walk an interviewer through.

**Database:** MongoDB (via Motor, the async driver) — stores every review
run so the dashboard has history and you can eventually build an evaluation
set from real data.

**Frontend:** React + Vite — a read-only dashboard that polls the backend
for review history and aggregate stats.

## Project structure

```
ai-code-review-agent/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + router registration
│   │   ├── config.py          # env var settings
│   │   ├── database.py        # MongoDB connection
│   │   ├── models.py          # Pydantic schemas
│   │   ├── github_client.py   # all GitHub API calls
│   │   ├── agent.py           # the AI review logic (the heart of the project)
│   │   └── routers/
│   │       ├── webhook.py     # POST /webhook/github
│   │       └── reviews.py     # GET /reviews, /reviews/stats
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js
    │   └── components/
    └── package.json
```

## Setup — Backend

1. `cd backend`
2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in:
   - `OPENAI_API_KEY` — from https://platform.openai.com/api-keys
   - `MONGODB_URI` — a free MongoDB Atlas cluster works fine, or run MongoDB locally
   - `GITHUB_TOKEN` and `GITHUB_WEBHOOK_SECRET` — see the GitHub setup section below
4. Run the server:
   ```
   uvicorn app.main:app --reload --port 8000
   ```
5. Visit `http://localhost:8000/docs` — FastAPI's auto-generated Swagger UI.
   You can test `/reviews` and `/reviews/stats` immediately even with an
   empty database (they'll return empty results).

## Setup — Frontend

1. `cd frontend`
2. `npm install`
3. Copy `.env.example` to `.env` (defaults are fine for local dev)
4. `npm run dev`
5. Visit `http://localhost:5173`

## Connecting a real GitHub repo (so it actually reviews real PRs)

1. **Get a token:** GitHub → Settings → Developer settings → Personal access
   tokens → generate one with `repo` scope. Put it in `GITHUB_TOKEN`.
2. **Expose your local backend to the internet** so GitHub's webhook can
   reach it — the easiest way for local dev is a tunnel:
   ```
   ngrok http 8000
   ```
   Copy the `https://...ngrok-free.app` URL it gives you.
3. **Create the webhook:** go to your repo → Settings → Webhooks → Add
   webhook.
   - Payload URL: `https://<your-ngrok-url>/webhook/github`
   - Content type: `application/json`
   - Secret: any random string — put the same value in `GITHUB_WEBHOOK_SECRET`
   - Events: select "Pull requests" only
4. Open a pull request on that repo (even a trivial one-line change to a
   test file). Within a few seconds you should see inline comments appear,
   and the review should show up in your dashboard.

## Deploying it for real (so it's a live link on your resume)

- **Backend:** Railway or Render — both support a `Dockerfile` or a plain
  Python service. Set the same env vars there as in your `.env`.
- **Frontend:** Vercel — connect your GitHub repo, set `VITE_API_URL` to
  your deployed backend's URL as an environment variable.
- **Database:** MongoDB Atlas free tier.
- Once deployed, point the GitHub webhook at your real backend URL instead
  of ngrok, and remove the tunnel.

## Interview prep — questions you should be able to answer about this

- **"Why structured output instead of just asking the model to write a
  review?"** — Structured JSON is what lets the code programmatically post
  comments to the right file/line and store results in a queryable schema.
  Free text would need fragile parsing.
- **"How do you know the webhook request really came from GitHub?"** —
  GitHub signs the payload with HMAC-SHA256 using your webhook secret; the
  backend recomputes the signature and compares it (`github_client.verify_signature`).
- **"What happens if the LLM returns malformed JSON?"** — The agent catches
  the parse error and fails soft (returns an empty result) rather than
  crashing the whole webhook handler — one bad LLM response shouldn't break
  the review for the whole PR.
- **"Why review file-by-file instead of the whole PR at once?"** — Smaller
  prompts are cheaper and faster, and it's easier to attribute an issue back
  to a specific file when you're not asking the model to track everything at once.
- **"What would you improve with more time?"** — See Roadmap below.

## Roadmap / stretch goals

- [ ] Auto-generate a suggested code patch, not just a text comment
- [ ] Slack/Discord notification when a review completes
- [ ] A small evaluation set of known-good/known-bad PRs to report a
      precision number in this README
- [ ] Support GitLab in addition to GitHub (would mean generalizing `github_client.py`)
- [ ] Auth on the dashboard if you make it public
