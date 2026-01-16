#!/bin/bash
export PATH=$PATH:/home/younlea/.local/bin
cd /home/younlea/source-code/daily_inform
/usr/bin/python3 local_update.py >> update.log 2>&1
