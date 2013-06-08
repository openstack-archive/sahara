# Copyright (c) 2013 Mirantis Inc.
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


def merge_configs(*configs):
    """Merge configs in special format.

    It supports merging of configs in the following format:
    applicable_target -> config_name -> config_value

    """
    result = {}
    for config in configs:
        if config:
            for a_target in config:
                if a_target not in result or not result[a_target]:
                    result[a_target] = {}
                result[a_target].update(config[a_target])

    return result
