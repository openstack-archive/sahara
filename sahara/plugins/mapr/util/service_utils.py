# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import six

from sahara.i18n import _


def get_node_process_name(node_process):
    # This import is placed here to avoid circular imports
    from sahara.plugins.mapr.domain import node_process as np  # noqa

    if isinstance(node_process, np.NodeProcess):
        return node_process.ui_name
    if isinstance(node_process, six.string_types):
        return node_process

    raise TypeError(_("Invalid argument type %s") % type(node_process))


def has_node_process(instance, node_process):
    node_process_name = get_node_process_name(node_process)
    instance_node_processes = instance.node_group.node_processes
    return node_process_name in instance_node_processes


def has_service(instance, service):
    return any(has_node_process(instance, node_process)
               for node_process in service.node_processes)


def filter_by_node_process(instances, node_process):
    return [instance for instance in instances
            if has_node_process(instance, node_process)]


def filter_by_service(instances, service):
    return [instance for instance in instances
            if has_service(instance, service)]
