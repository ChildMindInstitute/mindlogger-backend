#!/bin/bash
source /var/app/venv/staging-LQM1lest/bin/activate
source /opt/elasticbeanstalk/deployment/custom_env_var
cd /var/app/current
python girderformindlogger/external/clear_user_data.py
