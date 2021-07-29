#!/bin/bash
source /var/app/venv/staging-LQM1lest/bin/activate
source ~/env
cd /var/app/current
python girderformindlogger/external/scheduler.py
