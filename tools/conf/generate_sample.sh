#!/usr/bin/env bash
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 SINA Corporation
# All Rights Reserved.
# Author: Zhongyue Luo <lzyeval@gmail.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# stolen from the OpenStack Nova

FILES=$(find savanna -type f -name "*.py" ! -path "savanna/tests/*" -exec \
    grep -l "Opt(" {} \; | sort -u)
BINS=$(echo bin/savanna-*)

PYTHONPATH=./:${PYTHONPATH} \
    tools/with_venv python $(dirname "$0")/extract_opts.py \
    --whitelist-file tools/conf/whitelist.txt ${FILES} ${BINS} > \
    etc/savanna/savanna.conf.sample.raw

PYTHONPATH=./:${PYTHONPATH} \
    tools/with_venv python $(dirname "$0")/extract_opts.py \
    --blacklist-file tools/conf/blacklist.txt ${FILES} ${BINS} > \
    etc/savanna/savanna.conf.sample-full

# Remove compiled files created by imp.import_source()
for bin in ${BINS}; do
    [ -f ${bin}c ] && rm ${bin}c
done
