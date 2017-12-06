# Copyright (c) 2014 Mirantis Inc.
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


from oslo_utils import uuidutils

from sahara.conductor import resource as r


def create_cluster(name, tenant, plugin, version, node_groups, **kwargs):
    dct = {'id': uuidutils.generate_uuid(), 'name': name,
           'tenant_id': tenant, 'plugin_name': plugin,
           'hadoop_version': version, 'node_groups': node_groups,
           'cluster_configs': {}, "sahara_info": {},
           'user_keypair_id': None, 'default_image_id': None,
           'is_protected': False}
    dct.update(kwargs)
    return r.ClusterResource(dct)


def make_ng_dict(name, flavor, processes, count, instances=None,
                 volumes_size=None, node_configs=None, resource=False,
                 **kwargs):
    node_configs = node_configs or {}
    instances = instances or []
    dct = {'id': uuidutils.generate_uuid(), 'name': name,
           'volumes_size': volumes_size, 'flavor_id': flavor,
           'node_processes': processes, 'count': count,
           'instances': instances, 'node_configs': node_configs,
           'security_groups': None, 'auto_security_group': False,
           'availability_zone': None, 'volumes_availability_zone': None,
           'open_ports': [], 'is_proxy_gateway': False,
           'volume_local_to_instance': False}
    dct.update(kwargs)
    if resource:
        return r.NodeGroupTemplateResource(dct)
    return dct


def make_inst_dict(inst_id, inst_name, management_ip='1.2.3.4'):
    return {'instance_id': inst_id, 'instance_name': inst_name,
            'management_ip': management_ip}
