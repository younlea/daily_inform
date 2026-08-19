#!/bin/bash
export PATH=$PATH:/home/younlea/.local/bin
cd /home/younlea/source-code/daily_inform

exec 200>/tmp/daily_inform.lock
flock -n 200 || { echo "$(date): previous run still in progress, skipping" >> update.log; exit 0; }

/usr/bin/python3 local_update.py >> update.log 2>&1
