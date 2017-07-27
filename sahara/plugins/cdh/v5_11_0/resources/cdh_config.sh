#!/bin/bash

# prereqs - virtualenv

virtualenv venv
. venv/bin/activate

pip install cm-api

python cdh_config.py

deactivate

rm -rf venv
