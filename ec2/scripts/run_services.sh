#!/usr/bin/env bash

if [ -z "$1" ]
then
  echo "script name is required"
  exit
fi

service=$1

source /home/ec2-user/.bash_profile
source $(poetry env info --path)/bin/activate

poetry run python "$service"
