#!/bin/bash

# Work directory
cd $PROJECT_PATH
echo $APP "is started"

if [[ $APP = "worker" ]]
then
    python girderformindlogger/external/rq_worker.py
elif [[ $APP = "scheduler" ]]
then
    python girderformindlogger/external/scheduler.py
elif [[ $APP = "mind_logger" ]]
then
    girderformindlogger serve
fi
