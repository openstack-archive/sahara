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

import eventlet
from oslo.config import cfg

from savanna.openstack.common import log as logging
from savanna.service import cluster_ops
import savanna.storage.storage as storage
from savanna.utils.api import abort_and_log

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('allow_cluster_ops', 'savanna.config')


## Node Template ops:

def get_node_template(**args):
    return _node_template(storage.get_node_template(**args))


def get_node_templates(**args):
    return [_node_template(tmpl) for tmpl
            in storage.get_node_templates(**args)]


def create_node_template(values, headers):
    """Creates new node template from values dict.

    :param values: dict
    :return: created node template resource
    """
    values = values.pop('node_template')

    name = values.pop('name')
    node_type_id = storage.get_node_type(name=values.pop('node_type')).id
    tenant_id = headers['X-Tenant-Id']
    flavor_id = values.pop('flavor_id')

    nt = storage.create_node_template(name, node_type_id, tenant_id,
                                      flavor_id, values)

    return get_node_template(id=nt.id)


def terminate_node_template(**args):
    return storage.terminate_node_template(**args)


## Cluster ops:

def get_cluster(**args):
    return _cluster(storage.get_cluster(**args))


def get_clusters(**args):
    return [_cluster(cluster) for cluster in
            storage.get_clusters(**args)]


def create_cluster(values, headers):
    values = values.pop('cluster')

    name = values.pop('name')
    base_image_id = values.pop('base_image_id')
    tenant_id = headers['X-Tenant-Id']
    templates = values.pop('node_templates')

    # todo(slukjanov): check that we can create objects in the specified tenant

    cluster = storage.create_cluster(name, base_image_id, tenant_id, templates)

    eventlet.spawn(_cluster_creation_job, headers, cluster.id)

    return get_cluster(id=cluster.id)


def _cluster_creation_job(headers, cluster_id):
    cluster = storage.get_cluster(id=cluster_id)
    LOG.debug("Starting cluster '%s' creation: %s", cluster_id,
              _cluster(cluster).dict)

    if CONF.allow_cluster_ops:
        cluster_ops.launch_cluster(headers, cluster)
    else:
        LOG.info("Cluster ops are disabled, use --allow-cluster-ops flag")

    # update cluster status
    storage.update_cluster_status('Active', id=cluster.id)


def terminate_cluster(headers, **args):
    cluster = storage.update_cluster_status('Stopping', **args)

    eventlet.spawn(_cluster_termination_job, headers, cluster.id)


def _cluster_termination_job(headers, cluster_id):
    cluster = storage.get_cluster(id=cluster_id)
    LOG.debug("Stopping cluster '%s' creation: %s", cluster_id,
              _cluster(cluster).dict)

    if CONF.allow_cluster_ops:
        cluster_ops.stop_cluster(headers, cluster)
    else:
        LOG.info("Cluster ops are disabled, use --allow-cluster-ops flag")

    storage.terminate_cluster(id=cluster.id)


## Node Type ops:

def get_node_type(**args):
    return _node_type(storage.get_node_type(**args))


def get_node_types(**args):
    return [_node_type(t) for t in storage.get_node_types(**args)]


## Utils and DB object to Resource converters

def _clean_nones(obj):
    d_type = type(obj)
    if d_type is not dict or d_type is not list:
        return obj

    if d_type is dict:
        remove = []
        for key in obj:
            value = _clean_nones(obj.get(key))
            if value is None or len(value) == 0:
                remove.append(key)
        for key in remove:
            obj.pop(key)
    elif d_type is list:
        new_list = []
        for elem in obj:
            elem = _clean_nones(elem)
            if elem is not None and len(elem) == 0:
                new_list.append(elem)
        return new_list

    return obj


class Resource(object):
    def __init__(self, _name, _info):
        self._name = _name
        self._info = _clean_nones(_info)

    def __getattr__(self, k):
        if k not in self.__dict__:
            return self._info.get(k)
        return self.__dict__[k]

    def __repr__(self):
        return '<%s %s>' % (self._name, self._info)

    def __eq__(self, other):
        return self._name == other._name and self._info == other._info

    @property
    def dict(self):
        return self._info

    @property
    def wrapped_dict(self):
        return {self._name: self._info}


def _node_template(nt):
    if not nt:
        abort_and_log(404, 'NodeTemplate not found')
    d = {
        'id': nt.id,
        'name': nt.name,
        'node_type': {
            'name': nt.node_type.name,
            'processes': [p.name for p in nt.node_type.processes]},
        'flavor_id': nt.flavor_id
    }

    for conf in nt.node_template_configs:
        c_section = conf.node_process_property.node_process.name
        c_name = conf.node_process_property.name
        c_value = conf.value
        if c_section not in d:
            d[c_section] = dict()
        d[c_section][c_name] = c_value

    return Resource('node_template', d)


def _cluster(cluster):
    if not cluster:
        abort_and_log(404, 'Cluster not found')
    d = {
        'id': cluster.id,
        'name': cluster.name,
        'base_image_id': cluster.base_image_id,
        'status': cluster.status,
        'service_urls': {},
        'node_templates': {},
        'nodes': [{'vm_id': n.vm_id,
                   'node_template': {
                       'id': n.node_template.id,
                       'name': n.node_template.name
                   }}
                  for n in cluster.nodes]
    }
    for ntc in cluster.node_counts:
        d['node_templates'][ntc.node_template.name] = ntc.count

    for service in cluster.service_urls:
        d['service_urls'][service.name] = service.url

    return Resource('cluster', d)


def _node_type(nt):
    if not nt:
        abort_and_log(404, 'NodeType not found')

    d = {
        'id': nt.id,
        'name': nt.name,
        'processes': [p.name for p in nt.processes]
    }

    return Resource('node_type', d)
