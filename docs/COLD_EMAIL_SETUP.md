# Cold-email feature — setup (Hunter.io + Gmail OAuth)

The cold-email co-pilot needs two external credentials. The rest of the app
works fine without them (the endpoints just return 503 until configured).

## 1. Hunter.io (contact discovery)
1. Sign up at <https://hunter.io> (free tier).
2. Dashboard → **API** → copy your API key.
3. Put it in `backend/.env`:
   ```
   HUNTER_API_KEY=your_key
   ```

## 2. Google OAuth + Gmail API (draft creation)
1. Go to <https://console.cloud.google.com> → create/select a project.
2. **APIs & Services → Library →** enable **Gmail API**.
3. **APIs & Services → OAuth consent screen:**
   - User type: **External**, keep publishing status **Testing**.
   - Add scopes: `.../auth/gmail.compose` and `.../auth/userinfo.email`.
   - Under **Test users**, add your own Gmail address (and anyone else who'll demo it — up to 100).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID:**
   - Application type: **Web application**.
   - **Authorized redirect URIs:** add `http://localhost:8000/auth/google/callback`
     (and your deployed backend URL + `/auth/google/callback` later).
   - Create → copy the **Client ID** and **Client secret**.
5. Put them in `backend/.env`:
   ```
   GOOGLE_CLIENT_ID=...apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   FRONTEND_URL=http://localhost:5173
   ```
6. Restart the backend.

## How it works at runtime
- `POST /contacts {company}` → Hunter returns EM/senior-dev contacts.
- `POST /cold-email/draft` (résumé PDF + company + contact) → LLM writes a tailored email.
- **Connect Gmail:** the frontend sends you to `GET /auth/google/login` → Google consent →
  `/auth/google/callback` stores your tokens and redirects back with a `gmail_session` token.
- `POST /gmail/draft` (with header `X-Gmail-Session`) → creates the email in your Gmail
  **Drafts** folder. It is **never sent** — you review and send manually.

## Notes
- **Testing mode** means it works for you + added test users without Google's
  lengthy verification. Public access would require restricted-scope verification.
- We request only `gmail.compose` (least privilege for drafting).
- Cold outreach should stay 1:1 and personalized — drafts keep a human in the loop.

## Production (when deployed)
- Add the deployed backend's `/auth/google/callback` to the OAuth client's redirect URIs.
- Set `GOOGLE_REDIRECT_URI` to that URL and `FRONTEND_URL` to the Vercel URL on Render.
