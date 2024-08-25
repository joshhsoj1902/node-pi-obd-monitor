#!/bin/bash

sudo apt-get update

sudo apt-get install --no-install-recommends -y python3-pip python3-serial

python -m venv mazdaodb

source mazdaodb/bin/activate

pip install --upgrade setuptools wheel
pip install --upgrade prometheus_client pyserial
pip install --upgrade obd