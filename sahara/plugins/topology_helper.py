# Copyright (c) 2018 Red Hat, Inc.
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


from sahara.topology import topology_helper as t_helper

TOPOLOGY_CONFIG = t_helper.TOPOLOGY_CONFIG


def is_data_locality_enabled(**kwargs):
    return t_helper.is_data_locality_enabled()


def generate_topology_map(cluster, is_node_awareness, **kwargs):
    return t_helper.generate_topology_map(cluster, is_node_awareness)


def vm_awareness_core_config(**kwargs):
    return t_helper.vm_awareness_core_config()
