Here’s the quickest, no-nonsense path to deploy a Django app on **Render** with a cloud Postgres URL.

# 1) Minimal Django settings for production

In `settings.py`:

```python
import os
from pathlib import Path
import dj_database_url  # add to requirements.txt

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-not-secure")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = ["*"]  # or restrict to your Render host later

# DB: use your external Postgres URL from env
DATABASES = {
    "default": dj_database_url.config(conn_max_age=600, ssl_require=True)
}

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise for static files (simple + works well on PaaS)
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    # ...your apps
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ...your middleware
]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }
}
```

Why: Render expects you to serve the app with Gunicorn; static files are easy with **WhiteNoise** (no extra infra). ([whitenoise.readthedocs.io][1], [Django Project][2])

# 2) Add a lightweight health check (optional but handy)

```python
# core/views.py
from django.http import HttpResponse
def healthz(_): return HttpResponse("ok")

# core/urls.py
from django.urls import path
from .views import healthz
urlpatterns = [path("healthz/", healthz)]
```

Point Render’s health check to `/healthz/`.

# 3) Requirements

Your `requirements.txt` should include at least:

```
Django
gunicorn
dj-database-url
whitenoise
psycopg[binary]    # or psycopg2-binary
```

# 4) Procfile (or just use startCommand)

If you prefer a Procfile:

```
web: gunicorn yourproject.wsgi:application
```

# 5) Render blueprint (recommended)

Create `render.yaml` in repo root:

```yaml
services:
  - type: web
    name: django-app
    env: python
    plan: starter
    buildCommand: |
      pip install -r requirements.txt
      python manage.py collectstatic --noinput
      python manage.py migrate --noinput
    startCommand: gunicorn yourproject.wsgi:application
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.5
      - key: SECRET_KEY
        generateValue: true
      - key: DEBUG
        value: "0"
      - key: DATABASE_URL
        sync: false   # you’ll set this in the dashboard to your cloud DB URL
    healthCheckPath: /healthz/
```

Push this file, then in Render: **New → Blueprint** and select your repo. Render uses `render.yaml` to build and run your service. ([Render][3])

# 6) Environment variables (Render dashboard)

* **DATABASE\_URL**: paste your external Postgres connection string (include SSL; many providers require it).
  Example: `postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require`
  (Render’s own DBs expose connection URLs in the dashboard; with an external DB you just set this env var yourself.) ([Render][4], [Render][5], [Stack Overflow][6])

* **SECRET\_KEY**, **DEBUG=0**.

# 7) First deploy flow

1. Connect repo, select the Blueprint.
2. Set env vars (esp. `DATABASE_URL`).
3. Deploy; Render runs `buildCommand`, then `startCommand`.
4. Visit `https://<your-service>.onrender.com/healthz/` → “ok”.
5. Log in to Django admin after creating a superuser locally and migrating, or temporarily run:

   ```
   python manage.py createsuperuser
   ```

   (You can add this once locally and push data, or run via a one-off shell in Render.)

# 8) Static & media notes

* **Static**: handled by WhiteNoise + `collectstatic` in `buildCommand`. That’s enough for most apps. If you’ve got large/user-uploaded **media**, put those on S3/GCS; WhiteNoise is for static, not media. ([whitenoise.readthedocs.io][1], [Django Project][2])

# 9) Common gotchas (my take)

* **ALLOWED\_HOSTS** not set → 400 errors. Keep `["*"]` at first, then lock down.
* **Missing `collectstatic`** → no CSS/JS. Ensure it’s in `buildCommand`.
* **Wrong DB URL** or missing `sslmode` → connection failures. Add `sslmode=require` (or provider-specific flag) if your cloud DB needs it. ([Stack Overflow][6])

---

If you want, I can generate a ready-to-drop `settings.py` diff against your repo structure and a tailored `render.yaml` (app name, module path).

[1]: https://whitenoise.readthedocs.io/en/stable/django.html?utm_source=chatgpt.com "Using WhiteNoise with Django - Read the Docs"
[2]: https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/?utm_source=chatgpt.com "How to deploy static files"
[3]: https://render.com/docs/blueprint-spec?utm_source=chatgpt.com "Blueprint YAML Reference"
[4]: https://render.com/docs/postgresql-creating-connecting?utm_source=chatgpt.com "Create and Connect to Render Postgres"
[5]: https://community.render.com/t/how-can-i-access-external-database-url-via-an-environment-variable/21602?utm_source=chatgpt.com "How can I access *External* database url via an ..."
[6]: https://stackoverflow.com/questions/75069922/render-problem-connecting-to-the-remote-database?utm_source=chatgpt.com "Render - Problem connecting to the remote database"
