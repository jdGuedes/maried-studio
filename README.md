# Jewelry AI Studio Backend V1

Backend inicial do estúdio digital de semijoias.

## Stack
- Python 3.12+
- Django 6.x
- Django REST Framework 3.17.x
- SQLite no desenvolvimento; PostgreSQL preparado por `DATABASE_URL`
- OpenAI Image API encapsulada em `apps/ai/providers/openai.py`

## Regras do MVP
- 1 produto + 1 geração = 1 imagem = 1 crédito.
- Modos: `INSTAGRAM`, `MODEL`, `BODY_DETAIL`, `STILL`.
- Crédito é reservado antes da geração, consumido no sucesso e devolvido em falha técnica.
- `idempotency_key` evita duplicidade por clique/retry.
- Prompt final e snapshot de configuração ficam registrados na geração.

## Rodar localmente (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Endpoints V1
- `GET/POST /api/products/`
- `GET /api/studio/templates/?category=RING&mode=BODY_DETAIL`
- `POST /api/studio/generations/`
- `GET /api/studio/generations/{id}/`

## Próxima etapa
1. Criar migrations versionadas e seeds da Matriz Fotográfica V1.
2. Upload explícito da imagem original via endpoint dedicado.
3. Tirar o processamento OpenAI da requisição web e mover para fila/worker.
4. Autenticação por token/JWT.
5. Storage S3/Supabase em produção.
6. Telemetria real de custo/tokens retornados pela API.

## Carga inicial da Matriz Fotográfica
Após as migrations:
```powershell
python manage.py seed_studio
```

## Upload da imagem original
`POST /api/products/{product_id}/original-image/` usando `multipart/form-data` com o campo `file`.
