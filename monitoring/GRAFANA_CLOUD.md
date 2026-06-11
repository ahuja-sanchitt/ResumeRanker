# Grafana Cloud setup — metrics + logs (no Docker)

This ships both the **token/cache metrics** and the **app log lines** to Grafana
Cloud's free tier, using one small native agent (**Grafana Alloy**). It works
locally now and transfers to your deployed app later by changing the targets.

## 1. Create a free Grafana Cloud account
- Sign up at <https://grafana.com/auth/sign-up/create-user> → you get a "stack"
  with hosted Prometheus, Loki, and the Grafana UI.

## 2. Grab your connection credentials
In your stack, open **Connections → Add new connection**:
- **Hosted Prometheus metrics** → note the **remote-write URL** + **username (instance id)**.
- **Hosted Logs (Loki)** → note the **push URL** + **username (instance id)**.
- Create an **API token** (Account → Access Policies / API keys) with metrics-push
  and logs-push scope. You can reuse one token for both.

## 3. Create your real Alloy config from the template
The template is committed; the filled-in version (with your token) is gitignored.
```powershell
copy monitoring\alloy\config.alloy.example monitoring\alloy\config.alloy
```
Open `monitoring/alloy/config.alloy` and replace the 5 `<PLACEHOLDER>` values.
Adjust the log file path if your repo isn't at `C:/Users/sanch/Desktop/ResumeRanker`.

> ⚠️ `config.alloy` holds your real token and is **gitignored — never commit it**.
> Only `config.alloy.example` (placeholders) is tracked.

## 4. Install Grafana Alloy (Windows, no Docker)
- `winget install Grafana.Alloy`, or download the Windows release from
  <https://github.com/grafana/alloy/releases>. It's a single `alloy.exe`.

## 5. Run everything
```powershell
# Terminal 1 — backend (writes metrics + logs/app.log)
cd C:\Users\sanch\Desktop\ResumeRanker\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — the agent
cd C:\Users\sanch\Desktop\ResumeRanker\monitoring\alloy
alloy run config.alloy
```
Then make a few `/analyze` and `/interview-prep` calls at <http://127.0.0.1:8000/docs>
so there's data to ship.

## 6. View in Grafana Cloud
- **Metrics:** Dashboards → New → Import → upload
  `monitoring/grafana/provisioning/dashboards/resume-ranker.json`
  (pick your Grafana Cloud Prometheus as the datasource).
- **Logs:** Explore → select the **Loki** datasource → query `{job="resume-ranker"}`.
  Add `| logfmt` to parse fields, e.g.:
  `{job="resume-ranker"} | logfmt | endpoint="analyze"` → filter to analyze calls and
  chart `prompt_tokens` / `cached_tokens` over time.

## Later: pointing this at the deployed app
- **Metrics:** change the scrape target in `config.alloy` from `localhost:8000`
  to your public Render URL (host only, with `scheme = "https"` and port 443),
  or run Alloy beside the backend.
- **Logs:** instead of tailing a file, use **Render → Settings → Log Streams** to
  push stdout straight to your Loki push URL — no agent needed for logs in prod.
