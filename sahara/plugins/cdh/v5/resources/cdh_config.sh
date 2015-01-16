#!/bin/bash

tox -evenv -- python $(dirname $0)/cdh_config.py $*
