#!/bin/bash

cd /home/pi/dev/node-pi-obd-monitor

source mazdaodb/bin/activate

python obd-monitor.py
