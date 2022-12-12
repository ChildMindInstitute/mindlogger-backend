#!/bin/bash

## delete workers
pm2 delete all || echo 'No workers found'

## start workers
pm2 start /var/app/current/girderformindlogger/external/rq_worker.sh --name=worker_1
pm2 start /var/app/current/girderformindlogger/external/rq_worker.sh --name=worker_2

## start scheduler
pm2 start /var/app/current/girderformindlogger/external/rq_scheduler.sh
