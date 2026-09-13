#!/bin/bash
# ============================================================================
#  Meridian Goods — EC2 bootstrap script
#
#  HOW TO USE THIS FILE:
#  1. Create your RDS database FIRST (see the guide) and copy its endpoint.
#  2. Replace the 4 placeholder values below (look for "REPLACE_") with your
#     real values.
#  3. Paste the WHOLE file into the EC2 launch wizard's
#     "Advanced details" -> "User data" box before clicking Launch.
#
#  You do not need to SSH into anything — this script runs automatically
#  the first time the instance boots, and installs + starts the app for you.
#  Progress is logged to /var/log/user-data.log if you ever need to check it.
# ============================================================================
set -ex
exec > >(tee /var/log/user-data.log) 2>&1

DB_HOST="REPLACE_WITH_YOUR_RDS_ENDPOINT"
DB_PASSWORD="REPLACE_WITH_YOUR_DB_PASSWORD"
DB_USER="admin"
DB_NAME="meridian_goods"

dnf update -y
dnf install -y python3.11 python3.11-pip git

APP_DIR=/opt/meridian-goods
rm -rf $APP_DIR
git clone https://github.com/Rajshekhar6666/cloudtask-aws.git $APP_DIR
cd $APP_DIR/app

python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > /etc/systemd/system/meridian.service <<EOF
[Unit]
Description=Meridian Goods Flask app
After=network.target

[Service]
WorkingDirectory=$APP_DIR/app
Environment="DB_HOST=$DB_HOST"
Environment="DB_PORT=3306"
Environment="DB_USER=$DB_USER"
Environment="DB_PASSWORD=$DB_PASSWORD"
Environment="DB_NAME=$DB_NAME"
Environment="SECRET_KEY=meridian-goods-secret-key-change-me"
ExecStart=$APP_DIR/app/venv/bin/gunicorn -w 2 -b 0.0.0.0:80 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable meridian
systemctl start meridian

# One-time DB schema init + seed data
python3.11 -c "from app import app, init_db
with app.app_context():
    init_db()"
