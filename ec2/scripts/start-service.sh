#!/bin/bash -xe
source /home/ec2-user/.bash_profile

sudo systemctl daemon-reload
sudo systemctl start user-stream
sudo systemctl start signal-receiver
