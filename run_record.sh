#!/bin/bash
source .venv/bin/activate
cd source
python3.10 record.py yamlfile=service.yaml logfile=record_service.log
