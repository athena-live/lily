# Lily
![Lily](static/images/axiom.png)

Software design framework for identifying AI slop: outputs that look valid but fail under structure, logic, or execution.

Links:
- https://athena.live
- https://slop.fit

## Overview
Lily is a Django application focused on detecting, classifying, and explaining AI slop. See `SYSTEM_SPEC.md` for the full functional requirements and scope.

## Installation location and clone (server layout example)

Recommended directory layout on a server:

```
Django app: /opt/lily
Caddy configuration: /etc/caddy
```

Clone the repository (create the `lily` system user first, then clone as that user to avoid extra `chown` work):

```sh
sudo useradd --system --home /opt/lily --shell /usr/sbin/nologin lily
sudo mkdir -p /opt
sudo chown -R lily:lily /opt
sudo -u lily git clone <your-repo-url> /opt/lily
cd /opt/lily
```

## Configuration

Copy `.env.example` to `.env`:

```sh
cp .env.example .env
```

Use `.env.example` to see which environment variables are required. Keep secrets out of version control.

## Django setup (local)

Basic steps to run locally:

- Create and activate a virtual environment.
- Install dependencies.
- Load environment variables from `.env`.
- Run database migrations.
- Start the server.

Example (commands may vary by environment):

```sh
python -m venv .venv
source .venv/bin/activate
pip install django psycopg[binary]
set -a && source .env && set +a
python manage.py migrate
python manage.py runserver
```

## PostgreSQL install, hardening, and setup (optional)

Install PostgreSQL (Ubuntu/Debian):

```sh
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

Harden basic access and create the database/user:

```sql
-- Create a dedicated role
CREATE ROLE lily WITH LOGIN PASSWORD 'change-me';

-- Create the database owned by the role
CREATE DATABASE lily OWNER lily;

-- Lock down public privileges
REVOKE ALL ON DATABASE lily FROM PUBLIC;
GRANT ALL PRIVILEGES ON DATABASE lily TO lily;
```

Recommended PostgreSQL access controls (edit `pg_hba.conf`):

- Use `scram-sha-256` for password auth.
- Restrict access to the app server or private subnet only.

Example (adjust to your subnet):

```
host    lily    lily    10.0.0.0/24    scram-sha-256
```

Reload PostgreSQL after changes:

```sh
sudo systemctl reload postgresql
```

Update `.env` with your database settings:

```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=lily
DB_USER=lily
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=5432
```

## Reverse proxy and SSL (Caddy, optional)

This app can be proxied by Caddy for automatic HTTPS and certificate management. Typical flow: Caddy (80/443) -> Gunicorn -> Django.

Install Caddy (Ubuntu/Debian):

```sh
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

Production-ready `Caddyfile` (adjust domain, email, and static path). Caddy will redirect HTTP (80) to HTTPS (443):

```caddy
http://example.com {
  redir https://example.com{uri} permanent
}

example.com {
  encode zstd gzip
  tls you@example.com

  @static {
    path /static/*
  }
  handle @static {
    root * /opt/lily/staticfiles
    file_server
  }

  @media {
    path /media/*
  }
  handle @media {
    root * /opt/lily/media
    file_server
  }

  reverse_proxy unix//run/lily/gunicorn.sock

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "DENY"
    Referrer-Policy "no-referrer"
  }
}
```

## systemd service (Gunicorn, optional)

For production, run Django with Gunicorn behind Caddy. Create a systemd unit and point it to your virtualenv and project. Example `lily.service` (adjust paths, user, and environment). Prefer a dedicated system user/group instead of `www-data`.

```ini
[Unit]
Description=Lily Gunicorn App
After=network.target

[Service]
Type=simple
User=lily
Group=lily
WorkingDirectory=/opt/lily
EnvironmentFile=/opt/lily/.env
ExecStart=/opt/lily/.venv/bin/gunicorn lilly.wsgi:application \
  --bind unix:/run/lily/gunicorn.sock \
  --workers 3 \
  --timeout 600 \
  --graceful-timeout 360
Restart=on-failure
RestartSec=5
RuntimeDirectory=lily
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
```

Enable and start:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now lily.socket
sudo systemctl enable lily
```

Optional socket activation for graceful restarts:

```ini
[Unit]
Description=Lily Gunicorn Socket

[Socket]
ListenStream=/run/lily/gunicorn.sock
SocketUser=lily
SocketGroup=lily
SocketMode=0660

[Install]
WantedBy=sockets.target
```

## Note on static files and Caddy access

- Run `python manage.py collectstatic` so static assets land in `STATIC_ROOT` (default `/opt/lily/staticfiles`).
- Ensure the Caddy user can read that directory. On Ubuntu/Debian installs via the package manager, Caddy typically runs as the `caddy` user and group, so either use `chmod -R 755 /opt/lily/staticfiles` or add `caddy` to the `lily` group and set group read perms.

## Ports and firewall

- Open ports 80 and 443 on the web server for Caddy.
- Keep the Django app bound to a private interface (e.g., 127.0.0.1 or a private subnet).

## Deployment topologies

You can run everything on a single server or split responsibilities across multiple servers.

Single-server (simple)

- Caddy, Django app, and database all on one host.
- Fastest to set up; least isolation.

Two-server (web/app + data)

- Server A: Caddy + Django app
- Server B: Database only
- Database is not directly exposed to the internet.

Classic 3-tier (web, app, data) for stronger security

- Web server (Caddy): public internet, ports 80/443
- App server (Django): private subnet/VPN, no public exposure
- Data server (PostgreSQL): private subnet/VPN, no public exposure

For ultimate security, keep the app and data/persistence layers isolated behind a firewall or VPN.
