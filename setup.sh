#!/bin/bash

if [ -x ble_spo2/bin/activate ]; then
    echo "Python virtual environment already setup."
    source ble_spo2/bin/activate
else
    python3 -m venv ble_spo2
    source ble_spo2/bin/activate
    pip3 install -r requirements.txt
fi

#EOF
