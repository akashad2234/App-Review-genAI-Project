# Deployment: Vercel (frontend) + Railway (backend)

## Backend (Railway)

Already deployed at: `https://app-review-genai-project-production.up.railway.app`

- Set **CORS_ORIGINS** in Railway to allow your Vercel frontend:
  - Railway → your service → **Variables** → add:
  - `CORS_ORIGINS` = `https://your-app.vercel.app` (replace with your actual Vercel URL)
  - For preview deployments, add each URL or use a comma-separated list, e.g.  
    `https://your-app.vercel.app,https://your-app-git-main-yourteam.vercel.app`

## Frontend (Vercel)

1. **Import project**
   - [Vercel](https://vercel.com) → **Add New** → **Project** → import your GitHub repo `App-Review-genAI-Project`.

2. **Set root directory**
   - In **Configure Project**, set **Root Directory** to `frontend` (or **Edit** after import: Project **Settings** → **General** → **Root Directory** → `frontend`).

3. **Environment variable**
   - **Settings** → **Environment Variables** → add:
   - **Name:** `NEXT_PUBLIC_API_BASE_URL`
   - **Value:** `https://app-review-genai-project-production.up.railway.app`
   - Apply to **Production** (and **Preview** if you want preview deployments to use the same API).

4. **Deploy**
   - **Deploy** (or push to `main` after the project is connected). Vercel will run `npm run build` in the `frontend` folder.

5. **Allow CORS from Vercel**
   - After the first deploy, copy your Vercel URL (e.g. `https://app-review-genai-project.vercel.app`).
   - In **Railway** → your backend service → **Variables** → set:
   - `CORS_ORIGINS` = `http://localhost:3000,http://127.0.0.1:3000,https://your-actual-vercel-url.vercel.app`
   - Redeploy the backend if needed so the new CORS setting is applied.

The frontend will then call the Railway API from the browser; health and pulse endpoints should work.
