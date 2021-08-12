#!/bin/bash
source /var/app/venv/staging-LQM1lest/bin/activate
cd /var/app/current
python girderformindlogger/external/reschedule_notifications.py
