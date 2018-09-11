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

from sahara.tests.unit import testutils


def create_cluster(name, project, plugin, version, node_groups,
                   **kwargs):
    return testutils.create_cluster(name, project, plugin, version,
                                    node_groups, **kwargs)


def make_ng_dict(name, flavor, processes, count, instances=None,
                 volumes_size=None, node_configs=None, resource=False,
                 **kwargs):
    return testutils.make_ng_dict(name, flavor, processes, count,
                                  instances, volumes_size, node_configs,
                                  resource, **kwargs)


def make_inst_dict(inst_id, inst_name, management_ip='1.2.3.4', **kwargs):
    return testutils.make_inst_dict(inst_id, inst_name, management_ip)
