# ZERO SYNDICATE — Deploy GitHub + Cloudflare Pages + Render (Free Tier)

## Repository layout
- `public/` is the Cloudflare Pages website (HTML/CSS/JS only).
- `functions/api/[[path]].js` is an API proxy on the same website origin.
- `backend/` is the original Python FastAPI service with HTML file serving removed.
- `.gitignore` prevents `.env` files from being uploaded.

## 1. GitHub
Create a repository named `zero-syndicate` (private or public). Upload the **contents of this ZIP**, keeping `public`, `functions`, and `backend` folders at the **repository root**. Do not upload a ZIP as a single file.

## 2. Cloudflare Pages
Cloudflare Dashboard > Workers & Pages > Create application > Pages > Connect to Git > select repository.
- Production branch: `main`
- Framework preset: `None`
- Build command: `exit 0`
- Build output directory: `public`
- Root directory: repository root (leave blank/default)
- Deploy. The resulting URL will be `https://<project>.pages.dev`.

## 3. Render Python API (optional for first deploy, required for Astro/News/NARA)
Create a new Render Web Service from the SAME GitHub repository.
- Language: `Python`
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Plan: Free if available for the selected account/region.
After deployment test `https://<service>.onrender.com/api/health` and confirm the returned JSON contains `ok:true`.

## 4. Connect the API without editing JavaScript
Cloudflare > Workers & Pages > your Pages project > Settings > Variables and Secrets / Environment variables.
Add **BACKEND_URL** with the full HTTPS URL of the Render service, e.g. `https://<service>.onrender.com` (no trailing slash). Add it to Production, and Preview too if needed. Save and redeploy the site.
In browser test: `https://<project>.pages.dev/api/health`. Confirm `ok:true`.
Now Astro, News, NARA calls from app.js will go through your Pages Function to Render.

## 5. Advanced chat
NARA only interprets image pixels with a configured compatible model endpoint. If you have one, set CHAT_API_KEY, CHAT_API_URL, CHAT_MODEL in Render's Environment variables. Never put an API key in Cloudflare public variables or in JS/HTML. Optional capabilities depend on provider limits/fees.

## 6. Limitations
Cloudflare Pages is a static deployment host here: without Render the `/api` routes return 503. Render Free web services spin down after inactivity and can have cold starts. News is sourced from a third party and may be unavailable or restricted. Astrology BUY/SELL is exploratory and not a reliable trade signal. Check Swiss Ephemeris licensing before commercial use. This is a deploy-ready structure, NOT a guarantee of third-party connectivity or financial performance.

## Troubleshooting
- `404` home: check `public/index.html` and Pages build output `public`.
- `503` API: configure `BACKEND_URL` and redeploy.
- `502` API: check Render deployment, HTTPS URL, and logs.
- Calendar blank: check upstream economic feed availability and the selected date (weekly feed only).
- Image model unavailable: add valid model secrets in Render, ensure compatible endpoint/format.
