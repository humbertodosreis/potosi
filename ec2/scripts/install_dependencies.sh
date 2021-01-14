#!/bin/bash -xe
source /home/ec2-user/.bash_profile

cd /home/ec2-user/app/release

sudo cp ec2/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable user-stream
sudo systemctl enable signal-receiver

poetry env use 3.9
# shellcheck disable=SC1090
source $(poetry env info --path)/bin/activate
poetry install --no-dev --extras "pgsql"
