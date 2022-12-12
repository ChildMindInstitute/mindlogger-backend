#!/bin/bash

## (re)start workers
pm2 restart /var/app/current/girderformindlogger/external/rq_worker.sh --name=worker_1
pm2 restart /var/app/current/girderformindlogger/external/rq_worker.sh --name=worker_2

## start scheduler
pm2 restart /var/app/current/girderformindlogger/external/rq_scheduler.sh
