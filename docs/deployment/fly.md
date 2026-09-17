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

- Private media storage remains pending in `DEPLOY-002-FIX-002`.
- Shared Redis/cache remains pending in `SECURITY-002-P1-003`.
- Health/readiness endpoints remain pending in `DEPLOY-002-FIX-004`.
