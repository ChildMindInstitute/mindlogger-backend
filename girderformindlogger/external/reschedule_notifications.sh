#!/bin/bash
source /var/app/venv/staging-LQM1lest/bin/activate
source /opt/elasticbeanstalk/deployment/custom_env_var
cd /var/app/current
python girderformindlogger/external/reschedule_notifications.py
