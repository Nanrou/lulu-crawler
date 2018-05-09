#! /bin/bash

source ~/.profile
python /lulu-crawler/src/lulu/sword_fish.py
python /lulu-crawler/src/for_cron.py sf
