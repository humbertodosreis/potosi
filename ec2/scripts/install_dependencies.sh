#!/bin/bash -xe

function get_parameter () {
  local param="aws ssm get-parameter "

  if [ "$1" == "db_password" ]
  then
    param+=" --with-decryption"
  fi

  param+=" --name /potosi/$1 --query Parameter.Value"

  local param_value
  param_value=$(eval "$param")
  echo "$param_value" | sed -e 's/^"//' -e 's/"$//'
}

source /home/ec2-user/.bash_profile

cd /home/ec2-user/app/release

db_name=$(get_parameter db_name)
db_username=$(get_parameter db_username)
db_password=$(get_parameter db_password)
db_host=$(get_parameter db_host)
telegram_api_id=$(get_parameter telegram_api_id)
telegram_api_hash=$(get_parameter telegram_api_hash)
binance_api_key=$(get_parameter binance_api_key)
binance_api_secret=$(get_parameter binance_api_secret)
user_input_channel=$(get_parameter user_input_channel)

touch .env

cat > /home/ec2-user/app/release/.env << EOF
APP_ENV=production
APP_TELEGRAM_API_ID=$telegram_api_id
APP_TELEGRAM_API_HASH=$telegram_api_hash
APP_BINANCE_API_KEY=$binance_api_key
APP_BINANCE_API_SECRET=$binance_api_secret
APP_USER_INPUT_CHANNEL=$user_input_channel
DB_USER=$db_username
DB_PASSWORD=$db_password
DB_NAME=$db_name
DB_HOST=$db_host
DB_PORT=5432
EOF

poetry env use 3.9
# shellcheck disable=SC1090
source $(poetry env info --path)/bin/activate
poetry install --no-dev --extras "pgsql"

sudo cp ec2/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable user-stream
sudo systemctl enable signal-receiver
