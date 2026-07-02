# Put Modpools Ad Manager online (shareable link)

Goal: a web address your team just opens — nothing to install. We use
**Render.com** (free plan). Takes ~15 minutes, once.

You'll need:
- Your GitHub login (the repo already lives there).
- *(Optional)* a Claude API key from https://console.anthropic.com/ — only the
  "Create Ads" tab needs it; everything else works without.

---

## Steps

1. **Go to https://render.com and click "Get Started".** Choose **"Sign in with
   GitHub"** and approve access. (Render needs to read the repo to deploy it.)

2. On the Render dashboard, click **New +** (top right) → **Blueprint**.

3. **Connect the repository** `modpools-ad-studio` when Render lists your repos.
   If you don't see it, click "Configure account" / "Only select repositories",
   add `modpools-ad-studio`, and come back.

4. Render finds the `render.yaml` in the repo and shows a service called
   **modpools-ad-manager**. It will ask you to fill in two values:
   - **APP_PASSWORD** — make up a password your team will share to open the app
     (e.g. something only the 3 of you know). Write it down.
   - **ANTHROPIC_API_KEY** — paste your Claude key (or leave blank for now; you
     can add it later to turn on AI generation).

5. Click **Apply** / **Create**. Render installs and starts the app (first build
   takes a few minutes — you'll see logs scroll).

6. When it says **Live**, your address appears at the top, like
   `https://modpools-ad-manager.onrender.com`. Open it.

7. Your browser asks for a **username and password**:
   - Username: anything (type `team`)
   - Password: the **APP_PASSWORD** you chose in step 4.

That's it — share that link + the password with your 2 teammates.

---

## Good to know

- **Free plan sleeps.** After ~15 minutes of no use, the app naps and the next
  visit takes ~30 seconds to wake. Fine for internal use; upgrade Render's plan
  later if you want it always-on.
- **Data resets on redeploy** (the free plan uses temporary storage). Campaigns
  and settings you create will clear if the app restarts. When you're ready for
  permanent data, add a Render **PostgreSQL** database and set its connection
  string as the `DATABASE_URL` environment variable — ask and I'll walk you
  through it.
- **Still sandbox.** Posting is simulated; no real ad spend until a live platform
  adapter is connected.
- **Change the password / key** anytime in Render: your service → **Environment**
  → edit `APP_PASSWORD` / `ANTHROPIC_API_KEY` → save (it redeploys).
- **To update the app** after code changes: Render redeploys automatically when
  the branch updates, or click **Manual Deploy → Deploy latest commit**.
