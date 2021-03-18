#!/usr/bin/env bash

if [ -d venv ]; then
    source venv/bin/activate
fi

cd src/python
python3 -m stock_tracker
