# Deploying to Render

This puts the web app online at a public link. It takes about 15 minutes. Render's
free plan is enough. Menu names on Render's site change now and then, so if a label
below doesn't match exactly, look for the closest one.

## Before you start

- Your code must be pushed to GitHub (Render pulls it from there).
- Have your two API keys ready: the OpenAI key and the Tavily key (the same two that
  are in your local `.env` file). **Never put them in the code or on GitHub.**

## Step 1: Create the web service

1. Sign in at render.com (using your GitHub account is easiest).
2. Click **New +**, then **Web Service**, and choose your repository.
3. Fill in these settings:

| Setting | Value |
|---|---|
| Name | anything you like, for example `hantavirus-fact-checker` |
| Language / Runtime | Python 3 |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn server:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path (under Advanced) | `/health` |

The Python version comes from the `.python-version` file in this repo (3.12.16, the
same major version the GitHub tests run on). See "If the build fails" below.

## Step 2: Add the environment variables

Under **Environment** (or **Advanced**), add these three:

| Key | Value | What it is |
|---|---|---|
| `OPENAI_API_KEY` | your OpenAI key | lets the app call the AI model |
| `TAVILY_API_KEY` | your Tavily key | lets the app search CDC and WHO |
| `TRUSTED_PROXY_HOPS` | `1` to start | how many servers sit between a visitor and your app; see Step 4 |

Then click **Create Web Service**. The first build takes a few minutes.

## Step 3: Protect your money (do this before sharing the link)

- **OpenAI:** in your OpenAI account, go to Billing and set a **monthly budget limit**
  (a few dollars is plenty). This is a hard stop even if something goes wrong in the app.
- **Tavily:** the free plan includes 1,000 credits a month. Keep pay-as-you-go
  **off** so it stops at the limit instead of charging you.
- The app also limits each visitor to 10 checks per hour and the whole site to 25
  checks per day. Those counters live in memory, so they reset whenever the app
  restarts (this happens on Render's free plan), which is why the two limits above
  matter.

## Step 4: Check that the visitor limit works

The app tells visitors apart by their IP address. Behind Render, it needs to know how
many servers sit in front of it to read the right address. Check it once:

1. Open your site's link and run one claim from your laptop.
2. Open a second device on a different network (your phone on mobile data) and run one claim.
3. In Render, open **Logs**. Each check prints a line like
   `Check requested by visitor 203.0.113.5`.

What you should see: **two different addresses**, one for each device, and not an
address that starts with `10.` or `172.`.

- If both devices show the **same** address, or an address that isn't yours, change
  `TRUSTED_PROXY_HOPS` to `2`, redeploy, and repeat the check. (Try `3` if it still looks wrong.)
- Don't set it to `0` on Render. That would count every visitor as the same person.

The log line shows visitors' IP addresses, which is normal for a server log. You can
delete that one line in `server.py` later if you prefer.

## Step 5: Check that it works

- Open `https://YOUR-APP.onrender.com/health`. It should show `{"status":"ok"}`.
- Open the main page and check a claim, for example "Hantavirus is spread by mosquito bites."
  The answer should be FALSE with links to CDC or WHO pages.

## Good to know

- **Slow first load:** on the free plan, the app goes to sleep after about 15 minutes
  without visitors. The next visit takes up to a minute to wake it. This is normal.
- **Every push to `main` redeploys** the app automatically (you can turn that off in the settings).
- **Keep it to one instance.** The limits are counted in memory, so running more than one
  copy would give each copy its own counters.
- If you see a lot of "Daily limit reached" messages, the 25-per-day cap is working.
  You can raise `DAILY_LIMIT` in `server.py`, but remember that Tavily's free credits
  and your OpenAI budget are the real limits.

## If the build fails

- **"Python version not supported" or similar:** Render may not offer that exact patch
  number yet. Change the number in `.python-version` to one the build log says it accepts
  (keep it on 3.12 if you can, because that is the version GitHub's tests run on).
- **A package fails to install:** copy the error from the build log and look at the
  package named in it.
- **The site shows "The fact-check failed":** open the **Logs**. The error is printed there
  (most often a missing or wrong API key).
