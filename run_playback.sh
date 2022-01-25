#!/bin/bash
source .venv/bin/activate
cd source
python3.10 playback.py  yamlfile=service.yaml logfile=log/playback_service.log
