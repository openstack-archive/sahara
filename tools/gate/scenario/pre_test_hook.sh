#!/bin/bash
#
# Copyright (c) 2015 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script is executed inside pre_test_hook function in devstack gate.

set -ex

source commons $@

echo "IMAGE_URLS=$SAHARA_FAKE_PLUGIN_IMAGE" >> $LOCALRC_PATH

# Here we can set some configurations for local.conf
# for example, to pass some config options directly to sahara.conf file
# echo -e '[[post-config|$SAHARA_CONF]]\n[DEFAULT]\n' >> $LOCALCONF_PATH
# echo -e 'infrastructure_engine=true\n' >> $LOCALCONF_PATH

if [ "$NETWORK" == "nova-network" ]; then
    echo -e '[[post-config|$SAHARA_CONF_FILE]]\n[DEFAULT]\n' >> $LOCALCONF_PATH
    echo -e 'heat_enable_wait_condition=false\n' >> $LOCALCONF_PATH
fi
