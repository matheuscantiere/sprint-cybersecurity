.PHONY: lint test cov check

lint:
	ruff check .
	ruff format --check .

test:
	pytest

cov:
	pytest --cov=apps --cov-report=term-missing --cov-fail-under=85

check:
	DJANGO_SETTINGS_MODULE=config.settings.prod \
	DJANGO_ALLOWED_HOSTS=example.com \
	DJANGO_SECRET_KEY=placeholder-for-check-only-minimum-fifty-chars-aaaaaaaaaa \
	JWT_SIGNING_KEY=placeholder-jwt-for-check-only-minimum-sixty-four-chars-aaaaaaa \
	CRYPTOGRAPHY_KEY=placeholder-fernet-key-44-chars-base64-padding= \
	python manage.py check --deploy --fail-level=WARNING
