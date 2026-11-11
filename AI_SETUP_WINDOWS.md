# ResolveIQ v1.2 — Qwen2.5 via Ollama (automatic)

## What is real in this version

ResolveIQ tries to run actual **Qwen2.5:3b** inference using Ollama installed on the machine hosting the FastAPI server. It checks the real `GET http://127.0.0.1:11434/api/tags` endpoint, then sends the issue and retrieved playbooks to `POST /api/chat`. Output is parsed, validated, and **never executed automatically**. Suggested tasks are only created after human approval.

**Default is AUTO.** If Ollama is not running, model is missing, the network connection to the model fails, inference times out, or JSON is invalid, the app uses its existing deterministic offline workflow. It logs the *actual* engine in each issue's source/analysis. The dashboard status badge says **Qwen AI online** or **Rules fallback**, and you can click it to see why.

Ollama is **local** — it does not require internet once the model is downloaded. A deployed Render server will not use Ollama installed on your laptop; it needs Ollama on the **hosting server**, otherwise it correctly displays **Rules fallback**.

## Windows — step by step

1. Install the Ollama Windows app from https://ollama.com/download. Launch it.
2. Double-click `INSTALL_QWEN_WINDOWS.bat` inside ResolveIQ. This runs `ollama pull qwen2.5:3b`, a one-time download of approximately **1.9 GB**. Internet is needed for the download, **not** for subsequent local inference.
3. Verify with `ollama list` that `qwen2.5:3b` is installed. Ollama should run in the system tray; if it isn't running, open Ollama.
4. Double-click `START_WINDOWS.bat` and open http://localhost:8000.
5. Click the status badge in the header and select **Refresh AI status**. It should say **Qwen AI online**.
6. Create a **new issue**, then inspect its Analysis panel; its source should say **Ollama · qwen2.5:3b**. Sample issues created before this version remain labeled as seeded demos.
7. To test fallback, exit Ollama and refresh the status. Add another issue: its source should say **Offline rules · fallback**. Reopen Ollama and refresh to switch back automatically.

## If you're offline right now

If `qwen2.5:3b` has already been downloaded, it works without internet. If it was **never** downloaded, the app cannot generate with Qwen until the model files are present. In the meantime rule-based analysis continues to work; it is not falsely labeled as AI.

## Optional settings

Copy `.env.example` to `.env` only if you want to customize the defaults:

```ini
LLM_MODE=auto
LLM_MODEL=qwen2.5:3b
OLLAMA_URL=http://127.0.0.1:11434
LLM_TIMEOUT=60
```

- `LLM_MODE=auto` (default): choose Ollama only when the model is accessible; otherwise rules.
- `LLM_MODE=off`: always use offline rules.
- `LLM_MODE=on`: attempt Ollama; still safely fall back when unavailable (never blocks issue intake).
- `GET /api/engine`: programmatic live status and explanation.

Do not send real personal or incident data to the public prototype because it has no authentication or tenant isolation.

## Quick troubleshooting

- **Rules fallback: Ollama not running** — start Ollama, then use Refresh AI status.
- **Model not installed** — run `ollama pull qwen2.5:3b` when you have internet.
- **AI badge online but an individual issue says fallback** — the inference call failed/timed out or returned unusable JSON; check the Ollama logs, then try reanalyzing the issue.
- **Live Render deployment says fallback** — expected unless that server has its own Ollama instance. Your PC's Ollama is not accessible as Render's `localhost`.
