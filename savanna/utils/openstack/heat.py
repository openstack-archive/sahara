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

import json
import time

from heatclient import client as heat_client
from oslo.config import cfg

from savanna import context
from savanna.openstack.common import log as logging
from savanna.utils import files as f


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def client():
    ctx = context.current()
    #TODO(aignatov): make it as configurable option
    return heat_client.Client('1', 'http://localhost:8004/v1/%s' %
                              ctx.tenant_id, token=ctx.token)


def _get_inst_name(cluster_name, ng_name, index):
    return '%s-%s-%i' % (cluster_name, ng_name, (index + 1))


def _get_port_name(inst_name):
    return '%s-port' % inst_name


def _get_floating_name(inst_name):
    return '%s-floating' % inst_name


def _get_volume_name(inst_name, volume_idx):
    return '%s-volume-%i' % (inst_name, volume_idx)


def _get_volume_attach_name(inst_name, volume_idx):
    return '%s-volume-attachment-%i' % (inst_name, volume_idx)


def _load_template(template_name, fields):
    template_file = f.get_file_text('resources/%s' % template_name)
    return template_file.rstrip() % fields


def _prepare_userdata(userdata):
    """Converts userdata as a text into format consumable by heat template."""

    userdata = userdata.replace('"', '\\"')

    lines = userdata.splitlines()
    return '"' + '",\n"'.join(lines) + '"'


class ClusterTemplate(object):
    def __init__(self, cluster_name, fixed_net_id, user_keypair_id):
        self.cluster_name = cluster_name
        self.fixed_net_id = fixed_net_id
        self.user_keypair_id = user_keypair_id
        self.node_groups = {}

    def add_node_group(self, node_group_name, node_count, flavor_id, image_id,
                       userdata, floating_net_id, volumes_per_node,
                       volumes_size):

        self.node_groups[node_group_name] = {
            'node_count': node_count,
            'flavor_id': flavor_id,
            'image_id': image_id,
            'userdata': userdata,
            'floating_net_id': floating_net_id,
            'volumes_per_node': volumes_per_node,
            'volumes_size': volumes_size}

    # Consider using a single Jinja template for all this
    def instantiate(self, update_existing):
        # TODO(dmitryme): support anti-affinity

        main_tmpl = _load_template('main.heat',
                                   {'resources': self._serialize_resources()})

        heat = client()

        kwargs = {
            'stack_name': self.cluster_name,
            'timeout_mins': 180,
            'disable_rollback': False,
            'parameters': {},
            'template': json.loads(main_tmpl)}

        if not update_existing:
            heat.stacks.create(**kwargs)
        else:
            for stack in heat.stacks.list():
                if stack.stack_name == self.cluster_name:
                    stack.update(**kwargs)
                    break

        for stack in heat.stacks.list():
            if stack.stack_name == self.cluster_name:
                return ClusterStack(self, stack)

        raise RuntimeError('Failed to find just created stack %s' %
                           self.cluster_name)

    def _serialize_resources(self):
        resources = []

        for name, props in self.node_groups.iteritems():
            for idx in range(0, props['node_count']):
                resources.extend(self._serialize_instance(name, props, idx))

        return ',\n'.join(resources)

    def _serialize_instance(self, ng_name, ng_props, idx):
        inst_name = _get_inst_name(self.cluster_name, ng_name, idx)

        # TODO(dmitryme): support floating IPs for nova-network without
        # auto-assignment

        nets = ''
        if CONF.use_neutron:
            port_name = _get_port_name(inst_name)
            yield self._serialize_port(port_name, self.fixed_net_id)

            #nets = '"NetworkInterfaces" : [ { "Ref" : "%s" } ],' % port_name
            nets = '"networks" : [{ "port" : { "Ref" : "%s" }}],' % port_name

            if ng_props['floating_net_id']:
                yield self._serialize_floating(inst_name, port_name,
                                               ng_props['floating_net_id'])

        fields = {'instance_name': inst_name,
                  'flavor_id': ng_props['flavor_id'],
                  'image_id': ng_props['image_id'],
                  'network_interfaces': nets,
                  'key_name': self.user_keypair_id,
                  'userdata': _prepare_userdata(ng_props['userdata'])}

        yield _load_template('instance.heat', fields)

        for idx in range(0, ng_props['volumes_per_node']):
            yield self._serialize_volume(inst_name, idx,
                                         ng_props['volumes_size'])

    def _serialize_port(self, port_name, fixed_net_id):
        fields = {'port_name': port_name,
                  'fixed_net_id': fixed_net_id}

        return _load_template('neutron-port.heat', fields)

    def _serialize_floating(self, inst_name, port_name, floating_net_id):
        fields = {'floating_ip_name': _get_floating_name(inst_name),
                  'floating_net_id': floating_net_id,
                  'port_name': port_name}

        return _load_template('neutron-floating.heat', fields)

    def _serialize_volume(self, inst_name, volume_idx, volumes_size):
        fields = {'volume_name': _get_volume_name(inst_name, volume_idx),
                  'volumes_size': volumes_size,
                  'volume_attach_name': _get_volume_attach_name(inst_name,
                                                                volume_idx),
                  'instance_name': inst_name}

        return _load_template('volume.heat', fields)


class ClusterStack(object):
    def __init__(self, tmpl, heat_stack):
        self.tmpl = tmpl
        self.heat_stack = heat_stack

    def wait_till_active(self):
        while self.heat_stack.stack_status not in \
                ('CREATE_COMPLETE', 'UPDATE_COMPLETE'):
            time.sleep(1)
            self.heat_stack.get()

    def get_node_group_instances(self, node_group_name):
        insts = []

        count = self.tmpl.node_groups[node_group_name]['node_count']

        heat = client()
        for i in range(0, count):
            name = _get_inst_name(self.tmpl.cluster_name, node_group_name, i)
            res = heat.resources.get(self.heat_stack.id, name)
            insts.append((name, res.physical_resource_id))

        return insts
