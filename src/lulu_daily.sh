#! /bin/bash

source ~/.profile
python /lulu-crawler/src/lulu/core_logic.py
python /lulu-crawler/src/for_cron.py lulu
