#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/lily"
APP_USER="lily"
SERVICE_NAME="lily"
GIT_SSH_KEY="/home/lily/.ssh/athenalive"
STATIC_DIR="$APP_DIR/staticfiles"
MEDIA_DIR="$APP_DIR/media"

echo "➡️  Switching to app directory..."
cd "$APP_DIR"

echo "🔐 Ensuring app directory ownership..."
if [ "$(stat -c %U "$APP_DIR")" != "$APP_USER" ]; then
  chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

echo "🧹 Normalizing git permissions before pull..."
if [ -d "$APP_DIR/.git" ]; then
  chown -R "$APP_USER:$APP_USER" "$APP_DIR/.git"
  chmod -R u=rwX,g=rX,o=rX "$APP_DIR/.git"
fi

echo "🧱 Ensuring writable static/media directories..."
install -d -m 755 "$STATIC_DIR" "$MEDIA_DIR"
chown -R "$APP_USER:$APP_USER" "$STATIC_DIR" "$MEDIA_DIR"

echo "⬇️  Pulling latest changes..."
if [ -f "$GIT_SSH_KEY" ]; then
  sudo -u "$APP_USER" env GIT_SSH_COMMAND="ssh -i $GIT_SSH_KEY -o IdentitiesOnly=yes" \
    git -C "$APP_DIR" -c safe.directory="$APP_DIR" pull
else
  sudo -u "$APP_USER" git -C "$APP_DIR" -c safe.directory="$APP_DIR" pull
fi

echo "📦 Installing dependencies..."
sudo -u "$APP_USER" bash -c "
  source $APP_DIR/.venv/bin/activate
  pip install -r requirements.txt
"

echo "🗄️  Applying migrations..."
sudo -u "$APP_USER" bash -c "
  source $APP_DIR/.venv/bin/activate
  python manage.py migrate
"

echo "🎨 Collecting static files..."
sudo -u "$APP_USER" bash -c "
  source $APP_DIR/.venv/bin/activate
  python manage.py collectstatic --noinput
"

echo "🔐 Normalizing static/media ownership and permissions..."
chown -R "$APP_USER:$APP_USER" "$STATIC_DIR" "$MEDIA_DIR"
chmod -R u=rwX,g=rX,o=rX "$STATIC_DIR"
chmod -R u=rwX,g=rwX,o=rX "$MEDIA_DIR"

echo "🔁 Restarting service..."
sudo systemctl restart "$SERVICE_NAME"

echo "✅ Deployment completed successfully!"
