#!/usr/bin/env bash
# Manual smoke test for the full FIAP-Ford spreadsheet.
# Not part of CI — run after placing the xlsx in data/.
set -euo pipefail
docker compose exec web python manage.py import_catalog data/FIAP-Ford_-_Data_sheet_Desafio_01_v02.xlsx
docker compose exec web python manage.py import_catalog data/ranger_raptor_26my.csv --brand "Ford" --model "Ranger"
