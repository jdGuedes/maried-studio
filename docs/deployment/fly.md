# Fly.io Deployment Preparation

This repository is prepared for a future Fly.io deployment with separate runtime processes:

- Frontend: Next.js, built by `Dockerfile.frontend`.
- Backend web: Django WSGI, built by `Dockerfile.backend` and served by Gunicorn.
- Worker: same backend image, running `python manage.py process_generation_queue`.

No Fly app names are committed. Use the templates in `deploy/fly/*.example` when the deploy task defines the final app names and secrets.

## Production Commands

Frontend:

```sh
npm run start -- --hostname 0.0.0.0 --port ${PORT:-3000}
```

`NEXT_PUBLIC_API_URL` is read by the Next.js client bundle at build time. Set a different build arg for staging and production before building the frontend image; production builds fail fast when this value is missing.

Backend:

```sh
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout ${WEB_TIMEOUT:-120}
```

Worker:

```sh
python manage.py process_generation_queue
```

## Release Strategy

Database migrations should run as a Fly release command:

```sh
python manage.py migrate
```

Do not run migrations from the web or worker startup commands.

## Pending Deploy Dependencies

- Health/readiness endpoints remain pending in `DEPLOY-002-FIX-004`.

## Private Media Storage

Local development uses Django `FileSystemStorage`.

Staging and production use Django's `STORAGES` abstraction with Supabase Storage through its S3-compatible endpoint. The bucket must be private and provisioned outside application startup.

Required environment variable names:

- `DJANGO_MEDIA_STORAGE_BACKEND=supabase`
- `SUPABASE_STORAGE_ENDPOINT`
- `SUPABASE_STORAGE_REGION`
- `SUPABASE_STORAGE_BUCKET`
- `SUPABASE_STORAGE_ACCESS_KEY`
- `SUPABASE_STORAGE_SECRET_KEY`

Django Web and the generation worker must receive credentials for the same environment-specific bucket. Do not expose these values to the frontend.

Static files are not moved to Supabase Storage in this task.

Existing local media is not migrated automatically. If production media exists before enabling remote storage, handle it in `DEPLOY-STORAGE-MIGRATION-001`.

## Shared Cache / Rate Limiting

Local development uses Django `LocMemCache` and does not require Redis.

Staging and production must use a Redis-compatible shared cache through Django's Cache API. The application remains provider-neutral; Upstash or another Redis-compatible provider can be selected by infrastructure later.

Required environment variable names for staging/production:

- `DJANGO_CACHE_BACKEND=redis`
- `DJANGO_CACHE_KEY_PREFIX`
- `REDIS_URL`

Use `rediss://` for remote Redis in staging and production. Do not disable certificate verification.

`REDIS_URL` must be configured as a backend secret only. Never expose it to the frontend or any `NEXT_PUBLIC_*` variable.

Configuration missing or insecure in staging/production fails fast at settings load. Runtime Redis outages preserve the existing rate-limit fail-open behavior: security-sensitive requests continue, a safe warning is logged, and rate-limit protection is temporarily reduced.

Rate-limit counters are ephemeral security state. They are not business state and do not require the same backup policy as PostgreSQL or private object storage.

## Domain, Cookies, CORS, and CSRF

Local development uses HTTP localhost origins only:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Staging and production must provide explicit HTTPS configuration through environment variables:

- `FRONTEND_URL`
- `NEXT_PUBLIC_API_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SESSION_COOKIE_SECURE=true`
- `DJANGO_CSRF_COOKIE_SECURE=true`
- `DJANGO_SESSION_COOKIE_SAMESITE`
- `DJANGO_CSRF_COOKIE_SAMESITE`
- `DJANGO_SESSION_COOKIE_DOMAIN`
- `DJANGO_CSRF_COOKIE_DOMAIN`
- `DJANGO_SECURE_SSL_REDIRECT`
- `DJANGO_USE_X_FORWARDED_PROTO`

Staging and production reject localhost fallback, wildcard hosts, wildcard CORS origins, wildcard CSRF origins, and non-HTTPS origins.

The preferred production topology is same-site cross-origin subdomains:

- Frontend: `https://app.<domain>`
- API: `https://api.<domain>`

In that topology, the session cookie should remain host-only for the API whenever possible. The frontend must not read the session cookie; it only sends requests with `credentials: "include"`.

The frontend currently reads the `csrftoken` cookie and sends it as `X-CSRFToken`, so the CSRF cookie intentionally remains readable by JavaScript. If the final domain requires sharing the CSRF cookie across subdomains, configure `DJANGO_CSRF_COOKIE_DOMAIN` only for the CSRF cookie. Do not broaden `DJANGO_SESSION_COOKIE_DOMAIN` unless there is a proven need.

Use `SameSite=Lax` for same-site app/API subdomains when browser validation confirms the flow. Use `SameSite=None` only for a real cross-site staging topology, and only with secure cookies.

Fly terminates TLS before Django. `DJANGO_USE_X_FORWARDED_PROTO=true` prepares Django to honor `X-Forwarded-Proto`; validate this behavior in staging before enabling production traffic.

CORS is an allowlist for browser access, not authorization. Authentication, CSRF, permissions, private media authorization, and tenant isolation remain backend responsibilities.

Before staging homologation, run a real browser test and inspect DevTools for `Set-Cookie`, `Secure`, `SameSite`, `Domain`, CORS headers, CSRF bootstrap, login, `/me`, logout, password change, account recovery, private media, and rate limit behavior.
