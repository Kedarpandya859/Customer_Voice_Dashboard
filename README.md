# Review Opportunity Dashboard

Pulls reviews of one or more companies (currently **Meesho** and **Paytm**), tags sentiment and complaint patterns with Claude,
scores the recurring pain points, and generates product-opportunity
hypotheses — plus a one-pager report you can use as a cold-email hook.

## Architecture

1. **Collection** — `src/scrapers/play_store.py` (Play Store reviews; App Store/Reddit/Trustpilot can be added the same way)
2. **Tagging** — `src/pipeline/tag_reviews.py` (sentiment + complaint category via Claude Haiku)
3. **Opportunity mining** — `src/pipeline/generate_opportunities.py` (scores clusters, generates gap → product hypotheses via Claude Sonnet)
4. **Dashboard** — `dashboard/app.py` (trends, complaint breakdown, opportunity shortlist, raw data)
5. **Report generator** — `src/pipeline/generate_report.py` (one-pager + email-ready snippet per company)

## Setup

### 1. Create a free Postgres database (Supabase)
- [supabase.com](https://supabase.com) → New project
- Project Settings → Database → Connection string (URI mode) → copy it

### 2. Get a free Gemini API key
- [aistudio.google.com](https://aistudio.google.com) → Get API key. No credit card needed.
- The pipeline uses Gemini by default (`LLM_PROVIDER=gemini` in `.env`), which is free for this project's volume (~15 calls total).
- Have Anthropic credits instead? Set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` in `.env` — nothing else changes.

### 3. Local environment
```bash
git clone <your-repo-url>
cd meesho-review-dashboard
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: paste in DATABASE_URL, GEMINI_API_KEY, and optionally GEMINI_MODEL
```

If you see a Gemini model error, set `GEMINI_MODEL=gemini-2.5-flash` in `.env` and retry.
This repo is now compatible with the installed `google-genai` SDK using `client.models.generate_content()`.
If `gemini-2.5-flash` is unavailable, try `gemini-2.5-pro` or `gemini-flash-latest` instead.

### 4. Run the full pipeline, in order
```bash
python -m src.scrapers.play_store           # step 1: collect reviews
python -m src.pipeline.tag_reviews           # step 2: sentiment + category
python -m src.pipeline.generate_opportunities # step 3: score + generate hypotheses
python -m src.pipeline.generate_report        # step 5: report + email snippet
```
The report and email snippet land in `data/reports/`.

### 5. View the dashboard
```bash
streamlit run dashboard/app.py
```

## Deploying for free (so you have a live public link)

- **GitHub**: push this repo
- **GitHub Actions**: add repo secrets — `DATABASE_URL`, `LLM_PROVIDER` (set to `gemini`), `GEMINI_API_KEY`
  (Settings → Secrets and
  variables → Actions). The list of apps is set by `TARGET_APPS` at the top of the workflow
  file. `.github/workflows/pipeline.yml` then runs the
  entire pipeline daily for free and uploads the report as a downloadable
  artifact on each run.
- **Streamlit Community Cloud**: connect your GitHub repo at
  [share.streamlit.io](https://share.streamlit.io), set the same secrets in
  its secrets manager, deploy `dashboard/app.py`. You get a public URL —
  this is the link worth putting in a cold email.

### Quick deploy (recommended) — Streamlit Community Cloud

1. Push your repository to GitHub (create a new repo on GitHub and push):

```bash
git remote add origin git@github.com:<your-username>/<repo>.git
git branch -M main
git push -u origin main
```

2. Open https://share.streamlit.io and connect your GitHub account. Select
  the repository and set the app file to `dashboard/app.py`.

3. In Streamlit's Secrets (App settings → Secrets), add the same values you
  would for GitHub Actions: `DATABASE_URL`, `LLM_PROVIDER`, `GEMINI_API_KEY`, and optionally
  `GEMINI_MODEL` (e.g. `gemini-2.5-flash`).

4. Start the app — Streamlit will build the environment using
  `requirements.txt`. If you need more build control, add a `packages.txt`
  or a `apt.txt` at the repo root (Streamlit docs).

### Push + GitHub Actions

The repository already contains a GitHub Actions workflow at
`.github/workflows/pipeline.yml` which runs the scraping + pipeline daily
and uploads the generated report as an artifact. To enable it:

- In your repository on GitHub go to Settings → Secrets and variables → Actions
  and add: `DATABASE_URL`, `LLM_PROVIDER`, `GEMINI_API_KEY`, and `ANTHROPIC_API_KEY` (if using Anthropic).

Once those secrets are set, you can trigger the workflow manually from the
Actions tab or wait for the scheduled run.

### Deploying the dashboard to Vercel (container)

This repo includes a `Dockerfile` and `vercel.json` so you can deploy the
Streamlit dashboard on Vercel using a container deployment. Vercel will build
the Docker image and run the container.

1. Connect your GitHub repo to Vercel (https://vercel.com/new) and choose this
  repository.
2. In the Project Settings → Environment Variables, add the same secrets used
  by the pipeline: `DATABASE_URL`, `LLM_PROVIDER`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL`.
3. Deploy — Vercel will build the Docker image. The container runs Streamlit
  and binds to the port provided by Vercel.

Notes:
- Vercel runs containers for short-lived serverless deployments; for heavier
  or long-running Streamlit workloads you may prefer Render/Heroku/Streamlit
  Community Cloud which are more suited to long-lived web processes.
- If you encounter build issues, check the Vercel build logs and increase the
  image build resources or switch to a different host.

Lightweight Vercel alternative (recommended if Docker unsupported)

If Vercel cannot build containers for your account, you can host the
Streamlit server elsewhere (Render, Streamlit Community Cloud) and use Vercel
only for the public site. This repository includes a small serverless
function at `api/index.js` that returns a single-page app embedding the
external Streamlit URL via an iframe. To use it:

1. Deploy your Streamlit app on Render or Streamlit Community Cloud and note its public URL.
2. In Vercel Project Settings → Environment Variables add `STREAMLIT_URL` with that public URL.
3. Deploy the Vercel project — visiting the Vercel URL will show the embedded dashboard.

This approach serves the public website from Vercel while the Streamlit process runs on a host suited for long-lived containers.

## Choosing which companies to analyze

Set `TARGET_APPS` in `.env` and at the top of
`.github/workflows/pipeline.yml`. It's a `;`-separated list of
`Name|play.store.id|domain` entries:

```
TARGET_APPS=Meesho|com.meesho.supply|ecommerce;Paytm|net.one97.paytm|fintech
```

Every pipeline step loops over all of them, and the dashboard has a company
picker in the sidebar. Find an app id in its Play Store URL:
`play.google.com/store/apps/details?id=THIS_PART`. (The old single-app
`TARGET_APP_ID` / `TARGET_COMPANY_NAME` settings still work if `TARGET_APPS`
isn't set.)

`domain` picks the complaint taxonomy, defined in `TAXONOMIES` in
`src/config.py`:

| Domain | Used for | Categories |
|---|---|---|
| `ecommerce` | Meesho | delivery delay, product quality, refund issues, seller fraud, app bugs/UX, customer support, pricing |
| `fintech` | Paytm | payment failures, refund issues, KYC/account blocks, fraud & security, app bugs/UX, customer support, fees & charges |

For a different kind of product, add a new taxonomy there.
