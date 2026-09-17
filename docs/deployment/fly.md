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

`NEXT_PUBLIC_API_URL` is read by the Next.js client bundle at build time. Set a different build arg for staging and production before building the frontend image; otherwise the local development fallback may be compiled into the image.

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
