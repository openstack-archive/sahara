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

import novaclient.exceptions as nova_ex

import savanna.exceptions as ex
import savanna.plugins.base as plugin_base
import savanna.service.api as api
import savanna.utils.openstack.nova as nova


# Common validation checks
def check_plugin_name_exists(name):
    if name not in [p.name for p in api.get_plugins()]:
        raise ex.InvalidException("Savanna doesn't contain plugin with name %s"
                                  % name)


def check_plugin_supports_version(p_name, version):
    if version not in plugin_base.PLUGINS.get_plugin(p_name).get_versions():
        raise ex.InvalidException("Requested plugin '%s' doesn't support"
                                  " version '%s'" % (p_name, version))


def check_image_exists(image_id):
    try:
        # TODO(aignatov): Check supported images by plugin instead of it
        api.get_image(id=image_id)
    except nova_ex.NotFound:
        raise ex.InvalidException("Requested image '%s' not found"
                                  % image_id)


def check_flavor_exists(flavor_id):
    try:
        nova.client().flavors.get(flavor_id)
    except nova_ex.NotFound:
        raise ex.InvalidException("Requested flavor '%s' not found"
                                  % flavor_id)


def check_node_processes(plugin_name, version, node_processes):
    if len(set(node_processes)) != len(node_processes):
        raise ex.InvalidException("Duplicates in node processes "
                                  "have been detected")
    plugin_procesess = []
    for process in plugin_base.PLUGINS.get_plugin(
            plugin_name).get_node_processes(version).values():
        plugin_procesess += process

    if not set(node_processes).issubset(set(plugin_procesess)):
        raise ex.InvalidException("Plugin supports the following "
                                  "node procesess: " % plugin_procesess)


# Cluster creation related checks
def check_cluster_unique_name(name):
    if name in [cluster.name for cluster in api.get_clusters()]:
        raise ex.NameAlreadyExistsException("Cluster with name '%s' already"
                                            " exists" % name)


def check_keypair_exists(keypair):
    try:
        nova.client().keypairs.get(keypair)
    except nova_ex.NotFound:
        raise ex.InvalidException("Requested keypair '%s' not found" % keypair)


# Cluster templates creation related checks
def check_cluster_template_unique_name(name):
    if name in [t.name for t in api.get_cluster_templates()]:
        raise ex.NameAlreadyExistsException("Cluster template with name '%s'"
                                            " already exists" % name)


# NodeGroup templates related checks
def check_node_group_template_unique_name(name):
    if name in [t.name for t in api.get_node_group_templates()]:
        raise ex.NameAlreadyExistsException("NodeGroup template with name '%s'"
                                            " already exists" % name)
