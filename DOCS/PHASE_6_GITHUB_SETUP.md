# Phase 6: GitHub App Setup

This phase requires manual steps in the GitHub UI. Follow these instructions to register and configure the geekPR GitHub App.

## Step 6.1 — Register a GitHub App

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Fill in the form:
   - **App name**: `geekPR` (or any unique name)
   - **Homepage URL**: `http://localhost:3000` (or your server URL)
   - **Webhook URL**: `https://your-domain.com/api/webhook/github`
     - For local dev with ngrok: `https://abc123.ngrok.io/api/webhook/github`
   - **Webhook secret**: Generate a strong random string (e.g., `openssl rand -hex 32`)
3. **Permissions** — Set these exactly:
   - **Pull requests**: Read & Write
   - **Contents**: Read-only
   - **Metadata**: Read-only
4. **Subscribe to events**: Check **Pull request**
5. Click **Create GitHub App**

## Step 6.2 — Generate and Save the Private Key

1. On the app settings page, scroll to **Private keys**
2. Click **Generate a private key**
3. A `.pem` file will download
4. Move it to `backend/keys/geekpr.pem` (create the `keys/` folder if needed)
5. **Never commit this file** — it's already in `.gitignore`

```bash
mkdir -p /mnt/Media/Projects/geekPR/backend/keys
# Move the downloaded .pem file here
```

## Step 6.3 — Fill in `.env`

Edit `backend/.env` with the values from the GitHub App settings page:

```env
GITHUB_APP_ID=123456            # From "App ID" on settings page
GITHUB_PRIVATE_KEY_PATH=./keys/geekpr.pem
GITHUB_WEBHOOK_SECRET=your-random-secret-here
```

## Step 6.4 — Install the App on a Test Repo

1. Go to your GitHub App's public page: `https://github.com/apps/geekpr`
2. Click **Install**
3. Select the repo(s) you want to monitor
4. GitHub will now send webhook events to your endpoint

## Step 6.5 — Test with ngrok (Local Dev)

For local development, use ngrok to expose your backend to the internet:

```bash
ngrok http 8000
```

This gives you a public HTTPS URL like `https://abc123.ngrok.io`. Update the webhook URL in your GitHub App settings to:

```
https://abc123.ngrok.io/api/webhook/github
```

## Step 6.6 — Verify Setup

Once installed, open a PR on the test repo. You should see:

1. **Backend logs**: Webhook received and validated
2. **Celery worker logs**: Job enqueued and processing
3. **GitHub PR**: Review comment posted (if Ollama is running)

If nothing happens, check:
- Webhook deliveries: GitHub App → Settings → Webhook deliveries
- Backend logs: `uvicorn app.main:app --reload`
- Celery worker: `celery -A app.tasks.celery_app worker --loglevel=info`
- Redis: `redis-cli ping` should return `PONG`
- Ollama: `curl http://localhost:11434/api/tags`

---

**Next**: Once verified, move to Phase 7 (Docker & Deployment).
