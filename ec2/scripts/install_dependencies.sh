#!/bin/bash -xe

source /home/ec2-user/.bash_profile

cd /home/ec2-user/app/release

poetry env use 3.9
# shellcheck disable=SC1090
source $(poetry env info --path)/bin/activate
poetry install --no-dev --extras "pgsql"
