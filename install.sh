#!/bin/bash

python3 -m venv --without-pip venv
source venv/bin/activate
curl https://bootstrap.pypa.io/get-pip.py | python
deactivate
source venv/bin/activate
pip install -r requirements
deactivate