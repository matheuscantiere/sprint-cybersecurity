# FordSpy

API de inteligência competitiva automotiva — FIAP × Ford Challenge 01.

## Stack

- Python 3.12 / Django 5 / Django REST Framework
- PostgreSQL 16
- JWT (simplejwt) + RBAC (ADMIN / ANALYST / VIEWER)
- OpenAI GPT-4o-mini para insights

## Quickstart

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py import_catalog data/FIAP-Ford_-_Data_sheet_Desafio_01_v02.xlsx
```

- Swagger: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

## Testes

```bash
docker compose exec web pytest tests/unit
docker compose exec web pytest tests/integration
```

## Integrantes

| Nome | RM |
|---|---|
| Matheus Cantiere | 558479 |
| Guilherme Barbiero | 555185 |
| Marco Antonio Gonçalves | 556818 |
| Vinicius Castro | 556137 |
| Camila Mie Takara | 555418 |
