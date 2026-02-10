# Lilly
Software design framework for identifying AI slop, outputs that look valid but fail under structure, logic, or execution.

Links:
- https://athena.live
- https://slop.fit

## Overview
lily is a Django application focused on detecting, classifying, and explaining AI slop.

## Getting started

Prerequisites:
- Python 3.10+
- PostgreSQL

Setup:
```sh
python -m venv .venv
source .venv/bin/activate
pip install django psycopg[binary]
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials, then run:
```sh
python manage.py migrate
python manage.py runserver
```
