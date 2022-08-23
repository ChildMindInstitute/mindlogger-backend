#!/bin/bash
source /var/app/venv/staging-LQM1lest/bin/activate
export $(grep -v '^#' /opt/elasticbeanstalk/deployment/custom_env_var | xargs)
cd /var/app/current
python girderformindlogger/external/rq_worker.py
