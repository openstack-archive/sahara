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


from oslo_config import cfg
from oslo_log import log as logging
import six
import yaml

from sahara.utils import general as g
from sahara.utils.openstack import base as b
from sahara.utils.openstack import heat as h
from sahara.utils.openstack import neutron


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

SSH_PORT = 22


def _get_inst_name(ng):
    return {
        "list_join": [
            '-',
            [ng.cluster.name.lower(), ng.name.lower(),
             {"get_param": "instance_index"}]
        ]
    }


def _get_aa_group_name(cluster):
    return g.generate_aa_group_name(cluster.name)


def _get_port_name(ng):
    return {
        "list_join": [
            '-',
            [ng.cluster.name.lower(), ng.name.lower(),
             {"get_param": "instance_index"},
             "port"]
        ]
    }


def _get_floating_name(ng):
    return {
        "list_join": [
            '-',
            [ng.cluster.name.lower(), ng.name.lower(),
             {"get_param": "instance_index"},
             "floating"]
        ]
    }


def _get_floating_assoc_name(ng):
    return {
        "list_join": [
            '-',
            [ng.cluster.name.lower(), ng.name.lower(),
             {"get_param": "instance_index"},
             "floating", "assoc"]
        ]
    }


def _get_volume_name(ng):
    return {
        "list_join": [
            '-',
            [ng.cluster.name.lower(), ng.name.lower(),
             {"get_param": "instance_index"},
             "volume", {"get_param": "volume_index"}]
        ]
    }


class ClusterStack(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self.node_groups_extra = {}
        self.heat_stack = None

    def add_node_group_extra(self, node_group_id, node_count,
                             gen_userdata_func):
        self.node_groups_extra[node_group_id] = {
            'node_count': node_count,
            'gen_userdata_func': gen_userdata_func
        }

    def _get_main_template(self, files):
        outputs = {}
        resources = self._serialize_resources(files, outputs)
        return yaml.safe_dump({
            "heat_template_version": "2013-05-23",
            "description": "Data Processing Cluster by Sahara",
            "resources": resources,
            "outputs": outputs
        })

    def instantiate(self, update_existing, disable_rollback=True):
        files = {}
        main_tmpl = self._get_main_template(files)

        heat = h.client()

        kwargs = {
            'stack_name': self.cluster.name,
            'timeout_mins': 180,
            'disable_rollback': disable_rollback,
            'parameters': {},
            'template': main_tmpl,
            'files': files}

        if not update_existing:
            b.execute_with_retries(heat.stacks.create, **kwargs)
        else:
            stack = h.get_stack(self.cluster.name)
            b.execute_with_retries(stack.update, **kwargs)

        self.heat_stack = h.get_stack(self.cluster.name)

    def _need_aa_server_group(self, node_group):
        for node_process in node_group.node_processes:
            if node_process in self.cluster.anti_affinity:
                return True
        return False

    def _get_anti_affinity_scheduler_hints(self, node_group):
        if not self._need_aa_server_group(node_group):
            return {}

        return {"scheduler_hints": {"group": {"Ref": _get_aa_group_name(
            self.cluster)}}}

    def _serialize_resources(self, files, outputs):
        resources = {}

        if self.cluster.anti_affinity:
            resources.update(self._serialize_aa_server_group())

        for ng in self.cluster.node_groups:
            resources.update(self._serialize_ng_group(ng, files, outputs))

        return resources

    def _serialize_ng_group(self, ng, files, outputs):
        ng_file_name = "file://" + ng.name + ".yaml"
        files[ng_file_name] = self._serialize_ng_file(ng, files)

        outputs[ng.name + "-instances"] = {
            "value": {"get_attr": [ng.name, "instance"]}}

        return {
            ng.name: {
                "type": "OS::Heat::ResourceGroup",
                "properties": {
                    "count": self.node_groups_extra[ng.id]['node_count'],
                    "resource_def": {
                        "type": ng_file_name,
                        "properties": {"instance_index": "%index%"}
                    }
                }
            }
        }

    def _serialize_ng_file(self, ng, files):
        return yaml.safe_dump({
            "heat_template_version": "2013-05-23",
            "description": "Node Group {node_group} of "
                           "cluster {cluster}".format(node_group=ng.name,
                                                      cluster=ng.cluster.name),
            "parameters": {
                "instance_index": {
                    "type": "string"
                }},
            "resources": self._serialize_instance(ng, files),
            "outputs": {
                "instance": {"value": {
                    "physical_id": {"Ref": "inst"},
                    "name": {"get_attr": ["inst", "name"]}
                }}}
        })

    def _serialize_auto_security_group(self, ng):
        security_group_name = g.generate_auto_security_group_name(ng)
        security_group_description = (
            "Auto security group created by Sahara for Node Group "
            "'%s' of cluster '%s'." % (ng.name, ng.cluster.name))
        rules = self._serialize_auto_security_group_rules(ng)

        return {
            security_group_name: {
                "type": "AWS::EC2::SecurityGroup",
                "properties": {
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

    def _serialize_instance(self, ng, files):
        resources = {}
        properties = {}

        inst_name = _get_inst_name(ng)

        if ng.auto_security_group:
            resources.update(self._serialize_auto_security_group(ng))

        if CONF.use_neutron:
            port_name = _get_port_name(ng)
            resources.update(self._serialize_port(
                port_name, self.cluster.neutron_management_network,
                self._get_security_groups(ng)))

            properties["networks"] = [{"port": {"Ref": "port"}}]

            if ng.floating_ip_pool:
                resources.update(self._serialize_neutron_floating(ng))
        else:
            if ng.floating_ip_pool:
                resources.update(self._serialize_nova_floating(ng))

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
            "inst": {
                "type": "OS::Nova::Server",
                "properties": properties
            }
        })

        resources.update(self._serialize_volume(ng, files))

        return resources

    def _serialize_port(self, port_name, fixed_net_id, security_groups):
        properties = {
            "network_id": fixed_net_id,
            "replacement_policy": "AUTO",
            "name": port_name
        }
        if security_groups:
            properties["security_groups"] = security_groups

        return {
            "port": {
                "type": "OS::Neutron::Port",
                "properties": properties,
            }
        }

    def _serialize_neutron_floating(self, ng):
        return {
            "floating_ip": {
                "type": "OS::Neutron::FloatingIP",
                "properties": {
                    "floating_network_id": ng.floating_ip_pool,
                    "port_id": {"Ref": "port"}
                }
            }
        }

    def _serialize_nova_floating(self, ng):
        return {
            "floating_ip": {
                "type": "OS::Nova::FloatingIP",
                "properties": {
                    "pool": ng.floating_ip_pool
                }
            },
            "floating_ip_assoc": {
                "type": "OS::Nova::FloatingIPAssociation",
                "properties": {
                    "floating_ip": {"Ref": "floating_ip"},
                    "server_id": {"Ref": "inst"}
                }
            }
        }

    def _serialize_volume(self, ng, files):
        volume_file_name = "file://" + ng.name + "-volume.yaml"
        files[volume_file_name] = self._serialize_volume_file(ng)

        return {
            ng.name: {
                "type": "OS::Heat::ResourceGroup",
                "properties": {
                    "count": ng.volumes_per_node,
                    "resource_def": {
                        "type": volume_file_name,
                        "properties": {
                            "volume_index": "%index%",
                            "instance_index": {"get_param": "instance_index"},
                            "instance": {"Ref": "inst"}}
                    }
                }
            }
        }

    def _serialize_volume_file(self, ng):
        volume_name = _get_volume_name(ng)
        properties = {
            "name": volume_name,
            "size": six.text_type(ng.volumes_size)
        }
        if ng.volume_type:
            properties["volume_type"] = ng.volume_type

        if ng.volumes_availability_zone:
            properties["availability_zone"] = ng.volumes_availability_zone

        if ng.volume_local_to_instance:
            properties["scheduler_hints"] = {
                "local_to_instance": {"get_param": "instance"}}

        return yaml.safe_dump({
            "heat_template_version": "2013-05-23",
            "description": "Volume for node Group {node_group} of "
                           "cluster {cluster}".format(node_group=ng.name,
                                                      cluster=ng.cluster.name),
            "parameters": {
                "volume_index": {
                    "type": "string"
                },
                "instance_index": {
                    "type": "string"
                },
                "instance": {
                    "type": "string"
                }},
            "resources": {
                "volume": {
                    "type": "OS::Cinder::Volume",
                    "properties": properties
                },
                "volume-attachment": {
                    "type": "OS::Cinder::VolumeAttachment",
                    "properties": {
                        "instance_uuid": {"get_param": "instance"},
                        "volume_id": {"Ref": "volume"},
                        "mountpoint": None
                    }
                }},
            "outputs": {}
        })

    def _get_security_groups(self, node_group):
        if not node_group.auto_security_group:
            return node_group.security_groups

        return (list(node_group.security_groups or []) +
                [{"Ref": g.generate_auto_security_group_name(node_group)}])

    def _serialize_aa_server_group(self):
        server_group_name = _get_aa_group_name(self.cluster)
        return {
            server_group_name: {
                "type": "OS::Nova::ServerGroup",
                "properties": {
                    "name": server_group_name,
                    "policies": ["anti-affinity"]
                }
            }
        }

    def get_node_group_instances(self, node_group):
        for output in self.heat_stack.outputs:
            if output['output_key'] == node_group.name + "-instances":
                return output["output_value"]

        return []
