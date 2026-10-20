# Cloudflare Pages (iPhone) – AI FACTORY

Das Backend läuft auf Render und der Browser greift nur über die Cloudflare Pages Function unter `/api/*` darauf zu. Der OpenAI-Schlüssel (`MODEL_API_KEY`) verbleibt ausschließlich auf Render. Der Nutzer gibt in der Oberfläche nur den `FACTORY_TOKEN` ein, der von der Pages Function an Render weitergereicht wird.

1. GitHub: Inhalte dieser ZIP in das Repository übernehmen (bestehende Dateien ersetzen, neue `frontend/functions/api/[[path]].ts` hinzufügen). **Keine `.env` mit echten Schlüsseln committen.**
2. Cloudflare Dashboard > Workers & Pages > Create > **Pages** > GitHub-Repository `ai-factory` auswählen.
3. Framework preset: `None` (oder Next.js Static HTML Export, falls vorhanden).
4. Root directory (advanced): `frontend`.
5. Build command: `npm run build`.
6. Build output directory: `out`.
7. Environment Variables: `BACKEND_URL` = `https://ai-factory-hmtu.onrender.com` (kein abschließendes `/`). Keine anderen Secrets in Cloudflare setzen.
8. Deploy. Nach Veröffentlichung die `*.pages.dev`-Adresse öffnen, `FACTORY_TOKEN` eingeben und die Verbindung testen.

**Hinweise:** Render Free kann schlafen und verliert ohne externen persistenten Speicher Daten bei Deployment/Neustarts. Die auf Render bereits laufende Instanz nutzt ohne `DATABASE_URL` standardmäßig SQLite sowie lokale Projektdateien. Den Zugangsschlüssel nicht im GitHub-Repo oder als öffentliche Frontend-Umgebungsvariable hinterlegen. Falls `/api/settings` mit `401` antwortet, ist der Token falsch. Falls `502`, ist das Render-Backend nicht erreichbar. Modellaufrufe verursachen Kosten.
