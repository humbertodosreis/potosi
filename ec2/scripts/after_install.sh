#!/bin/bash -xe
function get_parameter () {
  local param="aws ssm get-parameter --region us-east-1"

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

cd /home/ec2-user/app/release || exit

echo "--- Set envs ---"

db_name=$(get_parameter db_name)
db_username=$(get_parameter db_username)
db_password=$(get_parameter db_password)
db_host=$(get_parameter db_host)
telegram_api_id=$(get_parameter telegram_api_id)
telegram_api_hash=$(get_parameter telegram_api_hash)
binance_api_key=$(get_parameter binance_api_key)
binance_api_secret=$(get_parameter binance_api_secret)
user_input_channel=$(get_parameter user_input_channel)

sudo touch .env
sudo chown ec2-user:ec2-user .env
chmod 640 .env

cat > /home/ec2-user/app/release/.env << EOF
APP_ENV=production
APP_TELEGRAM_API_ID="$telegram_api_id"
APP_TELEGRAM_API_HASH=$telegram_api_hash
APP_BINANCE_API_KEY=$binance_api_key
APP_BINANCE_API_SECRET=$binance_api_secret
APP_USER_INPUT_CHANNEL=$user_input_channel
APP_DB_USER=$db_username
APP_DB_PASSWORD=$db_password
APP_DB_NAME=$db_name
APP_DB_HOST=$db_host
APP_DB_PORT=5432
EOF

echo "--- make data dir ---"
sudo mkdir -p data
sudo chown ec2-user:ec2-user data

echo "--- run migrations ---"
poetry env use 3.9
# shellcheck disable=SC1090
source $(poetry env info --path)/bin/activate
poetry run python potosi/migration.py

echo "--- Starting services ---"
sudo cp ec2/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable user-stream
sudo systemctl enable signal-receiver
