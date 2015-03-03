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

import json

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara.utils import general as g
from sahara.utils.openstack import heat as h
from sahara.utils.openstack import neutron


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

SSH_PORT = 22


def _get_inst_name(cluster_name, ng_name, index):
    return g.generate_instance_name(cluster_name, ng_name, index + 1)


def _get_aa_group_name(cluster_name):
    return g.generate_aa_group_name(cluster_name)


def _get_port_name(inst_name):
    return '%s-port' % inst_name


def _get_floating_name(inst_name):
    return '%s-floating' % inst_name


def _get_floating_assoc_name(inst_name):
    return '%s-floating-assoc' % inst_name


def _get_volume_name(inst_name, volume_idx):
    return '%s-volume-%i' % (inst_name, volume_idx)


def _get_volume_attach_name(inst_name, volume_idx):
    return '%s-volume-attachment-%i' % (inst_name, volume_idx)


class ClusterTemplate(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self.node_groups_extra = {}

    def add_node_group_extra(self, node_group_id, node_count,
                             gen_userdata_func):
        self.node_groups_extra[node_group_id] = {
            'node_count': node_count,
            'gen_userdata_func': gen_userdata_func
        }

    def _get_main_template(self):
        return json.dumps({
            "AWSTemplateFormatVersion": "2010-09-09",
            "Description": "Data Processing Cluster by Sahara",
            "Resources": self._serialize_resources(),
            "Outputs": {}
        })

    def instantiate(self, update_existing, disable_rollback=True):
        main_tmpl = self._get_main_template()

        heat = h.client()

        kwargs = {
            'stack_name': self.cluster.name,
            'timeout_mins': 180,
            'disable_rollback': disable_rollback,
            'parameters': {},
            'template': main_tmpl}

        if not update_existing:
            heat.stacks.create(**kwargs)
        else:
            for stack in heat.stacks.list():
                if stack.stack_name == self.cluster.name:
                    stack.update(**kwargs)
                    break

        return ClusterStack(self, h.get_stack(self.cluster.name))

    def _need_aa_server_group(self, node_group):
        for node_process in node_group.node_processes:
            if node_process in self.cluster.anti_affinity:
                return True
        return False

    def _get_anti_affinity_scheduler_hints(self, node_group):
        if not self._need_aa_server_group(node_group):
            return {}

        return {"scheduler_hints": {"group": {"Ref": _get_aa_group_name(
            self.cluster.name)}}}

    def _serialize_resources(self):
        resources = {}

        if self.cluster.anti_affinity:
            resources.update(self._serialize_aa_server_group())

        for ng in self.cluster.node_groups:
            if ng.auto_security_group:
                resources.update(self._serialize_auto_security_group(ng))
            for idx in range(0, self.node_groups_extra[ng.id]['node_count']):
                resources.update(self._serialize_instance(ng, idx))

        return resources

    def _serialize_auto_security_group(self, ng):
        security_group_name = g.generate_auto_security_group_name(ng)
        security_group_description = (
            "Auto security group created by Sahara for Node Group "
            "'%s' of cluster '%s'." % (ng.name, ng.cluster.name))
        rules = self._serialize_auto_security_group_rules(ng)

        return {
            security_group_name: {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": security_group_description,
                    "SecurityGroupIngress": rules
                }
            }
        }

    def _serialize_auto_security_group_rules(self, ng):
        create_rule = lambda cidr, proto, from_port, to_port: {
            "CidrIp": cidr,
            "IpProtocol": proto,
            "FromPort": six.text_type(from_port),
            "ToPort": six.text_type(to_port)}

        rules = []
        for port in ng.open_ports:
            rules.append(create_rule('0.0.0.0/0', 'tcp', port, port))

        rules.append(create_rule('0.0.0.0/0', 'tcp', SSH_PORT, SSH_PORT))

        # open all traffic for private networks
        if CONF.use_neutron:
            for cidr in neutron.get_private_network_cidrs(ng.cluster):
                for protocol in ['tcp', 'udp']:
                    rules.append(create_rule(cidr, protocol, 1, 65535))
                rules.append(create_rule(cidr, 'icmp', -1, -1))

        return rules

    def _serialize_instance(self, ng, idx):
        resources = {}
        properties = {}

        inst_name = _get_inst_name(self.cluster.name, ng.name, idx)

        if CONF.use_neutron:
            port_name = _get_port_name(inst_name)
            resources.update(self._serialize_port(
                port_name, self.cluster.neutron_management_network,
                self._get_security_groups(ng)))

            properties["networks"] = [{"port": {"Ref": port_name}}]

            if ng.floating_ip_pool:
                resources.update(self._serialize_neutron_floating(
                    inst_name, port_name, ng.floating_ip_pool))
        else:
            if ng.floating_ip_pool:
                resources.update(self._serialize_nova_floating(
                    inst_name, ng.floating_ip_pool))

            if ng.security_groups:
                properties["security_groups"] = self._get_security_groups(ng)

        # Check if cluster contains user key-pair and include it to template.
        if self.cluster.user_keypair_id:
            properties["key_name"] = self.cluster.user_keypair_id

        gen_userdata_func = self.node_groups_extra[ng.id]['gen_userdata_func']
        userdata = gen_userdata_func(ng, inst_name)

        if ng.availability_zone:
            properties["availability_zone"] = ng.availability_zone

        properties.update(self._get_anti_affinity_scheduler_hints(ng))

        properties.update({
            "name": inst_name,
            "flavor": six.text_type(ng.flavor_id),
            "image": ng.get_image_id(),
            "admin_user": ng.image_username,
            "user_data": userdata
        })

        resources.update({
            inst_name: {
                "Type": "OS::Nova::Server",
                "Properties": properties
            }
        })

        for idx in range(0, ng.volumes_per_node):
            resources.update(self._serialize_volume(
                inst_name, idx, ng.volumes_size, ng.volumes_availability_zone,
                ng.volume_type, ng.volume_local_to_instance))

        return resources

    def _serialize_port(self, port_name, fixed_net_id, security_groups):
        properties = {
            "network_id": fixed_net_id,
            "replacement_policy": "AUTO"
        }
        if security_groups:
            properties["security_groups"] = security_groups

        return {
            port_name: {
                "Type": "OS::Neutron::Port",
                "Properties": properties
            }
        }

    def _serialize_neutron_floating(self, inst_name, port_name,
                                    floating_net_id):
        floating_ip_name = _get_floating_name(inst_name)

        return {
            floating_ip_name: {
                "Type": "OS::Neutron::FloatingIP",
                "Properties": {
                    "floating_network_id": floating_net_id,
                    "port_id": {"Ref": port_name}
                }
            }
        }

    def _serialize_nova_floating(self, inst_name, floating_pool_name):
        floating_ip_name = _get_floating_name(inst_name)
        floating_ip_assoc_name = _get_floating_assoc_name(inst_name)
        return {
            floating_ip_name: {
                "Type": "OS::Nova::FloatingIP",
                "Properties": {
                    "pool": floating_pool_name
                }
            },
            floating_ip_assoc_name: {
                "Type": "OS::Nova::FloatingIPAssociation",
                "Properties": {
                    "floating_ip": {"Ref": floating_ip_name},
                    "server_id": {"Ref": inst_name}
                }
            }
        }

    def _serialize_volume(self, inst_name, volume_idx, volumes_size,
                          volumes_availability_zone, volume_type,
                          volume_local_to_instance):
        volume_name = _get_volume_name(inst_name, volume_idx)
        volume_attach_name = _get_volume_attach_name(inst_name, volume_idx)
        properties = {
            "name": volume_name,
            "size": six.text_type(volumes_size),
            "volume_type": volume_type
        }
        if volumes_availability_zone:
            properties["availability_zone"] = volumes_availability_zone

        if volume_local_to_instance:
            properties["scheduler_hints"] = {
                "local_to_instance": {"Ref": inst_name}}

        return {
            volume_name: {
                "Type": "OS::Cinder::Volume",
                "Properties": properties
            },
            volume_attach_name: {
                "Type": "OS::Cinder::VolumeAttachment",
                "Properties": {
                    "instance_uuid": {"Ref": inst_name},
                    "volume_id": {"Ref": volume_name},
                    "mountpoint": None
                }
            }
        }

    def _get_security_groups(self, node_group):
        if not node_group.auto_security_group:
            return node_group.security_groups

        return (list(node_group.security_groups or []) +
                [{"Ref": g.generate_auto_security_group_name(node_group)}])

    def _serialize_aa_server_group(self):
        server_group_name = _get_aa_group_name(self.cluster.name)
        return {
            server_group_name: {
                "Type": "OS::Nova::ServerGroup",
                "Properties": {
                    "name": server_group_name,
                    "policies": ["anti-affinity"]
                }
            }
        }


class ClusterStack(object):
    def __init__(self, tmpl, heat_stack):
        self.tmpl = tmpl
        self.heat_stack = heat_stack

    def get_node_group_instances(self, node_group):
        insts = []

        count = self.tmpl.node_groups_extra[node_group.id]['node_count']

        heat = h.client()
        for i in range(0, count):
            name = _get_inst_name(self.tmpl.cluster.name, node_group.name, i)
            res = heat.resources.get(self.heat_stack.id, name)
            insts.append((name, res.physical_resource_id))

        return insts
