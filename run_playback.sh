#!/bin/bash
source .venv/bin/activate
cd source
python3.10 playback.py
systemctl stop mme-record.service
