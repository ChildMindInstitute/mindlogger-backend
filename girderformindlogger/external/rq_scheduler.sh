#!/bin/bash
source /opt/python/run/venv/bin/activate
source /opt/python/current/env
cd /opt/python/current/app
python girderformindlogger/external/scheduler.py
