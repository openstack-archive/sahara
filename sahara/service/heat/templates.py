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

from sahara.plugins import provisioning as plugin_provisioning
from sahara.service.heat import commons as heat_common
from sahara.utils import general as g
from sahara.utils.openstack import base as b
from sahara.utils.openstack import heat as h
from sahara.utils.openstack import neutron

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

SSH_PORT = 22
INSTANCE_RESOURCE_NAME = "inst"

heat_engine_opts = [
    cfg.BoolOpt(
        'heat_enable_wait_condition', default=True,
        help="Enable wait condition feature to reduce polling during cluster "
             "creation")
]
CONF.register_opts(heat_engine_opts)


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


def _get_wc_handle_name(inst_name):
    return '%s-wc-handle' % inst_name


def _get_wc_waiter_name(inst_name):
    return '%s-wc-waiter' % inst_name


class ClusterStack(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self.node_groups_extra = {}
        self.files = {}
        self.last_updated_time = None
        self.base_info = (
            "Data Processing Cluster by Sahara\n"
            "Sahara cluster name: {cluster}\n"
            "Sahara engine: {version}".format(
                cluster=cluster.name, version=heat_common.HEAT_ENGINE_VERSION)
        )

    def _node_group_description(self, ng):
        return "{info}\nNode group {node_group}".format(
            info=self.base_info, node_group=ng.name)

    def _asg_for_node_group_description(self, ng):
        return ("{info}\n"
                "Auto security group for Sahara Node Group: "
                "{node_group}".format(info=self.base_info, node_group=ng.name))

    def _volume_for_node_group_description(self, ng):
        return ("{info}\n"
                "Volume for Sahara Node Group {node_group}".format(
                    node_group=ng.name, info=self.base_info))

    def add_node_group_extra(self, node_group_id, node_count,
                             gen_userdata_func):
        self.node_groups_extra[node_group_id] = {
            'node_count': node_count,
            'gen_userdata_func': gen_userdata_func
        }

    def _get_main_template(self):
        outputs = {}
        resources = self._serialize_resources(outputs)
        return yaml.safe_dump({
            "heat_template_version": "2013-05-23",
            "description": self.base_info,
            "resources": resources,
            "outputs": outputs
        })

    def instantiate(self, update_existing, disable_rollback=True):
        main_tmpl = self._get_main_template()

        kwargs = {
            'stack_name': self.cluster.stack_name,
            'timeout_mins': 180,
            'disable_rollback': disable_rollback,
            'parameters': {},
            'template': main_tmpl,
            'files': self.files}

        if CONF.heat_stack_tags:
            kwargs['tags'] = ",".join(CONF.heat_stack_tags)

        if not update_existing:
            LOG.debug("Creating Heat stack with args: {args}"
                      .format(args=kwargs))
            b.execute_with_retries(h.client().stacks.create, **kwargs)
        else:
            stack = h.get_stack(self.cluster.stack_name)
            self.last_updated_time = stack.updated_time
            LOG.debug("Updating Heat stack {stack} with args: "
                      "{args}".format(stack=stack, args=kwargs))
            b.execute_with_retries(stack.update, **kwargs)

    def _need_aa_server_group(self, node_group):
        for node_process in node_group.node_processes:
            if node_process in self.cluster.anti_affinity:
                return True
        return False

    def _get_anti_affinity_scheduler_hints(self, node_group):
        if not self._need_aa_server_group(node_group):
            return {}

        return {
            "scheduler_hints": {
                "group": {
                    "get_resource": _get_aa_group_name(
                        self.cluster)
                }
            }
        }

    def _serialize_resources(self, outputs):
        resources = {}

        if self.cluster.anti_affinity:
            resources.update(self._serialize_aa_server_group())

        for ng in self.cluster.node_groups:
            resources.update(self._serialize_ng_group(ng, outputs))

        return resources

    def _serialize_ng_group(self, ng, outputs):
        ng_file_name = "file://" + ng.name + ".yaml"
        self.files[ng_file_name] = self._serialize_ng_file(ng)

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

    def _serialize_ng_file(self, ng):
        return yaml.safe_dump({
            "heat_template_version": "2013-05-23",
            "description": self._node_group_description(ng),
            "parameters": {
                "instance_index": {
                    "type": "string"
                }},
            "resources": self._serialize_instance(ng),
            "outputs": {
                "instance": {"value": {
                    "physical_id": {"get_resource": INSTANCE_RESOURCE_NAME},
                    "name": {"get_attr": [INSTANCE_RESOURCE_NAME, "name"]}
                }}}
        })

    def _serialize_auto_security_group(self, ng):
        security_group_name = g.generate_auto_security_group_name(ng)
        security_group_description = self._asg_for_node_group_description(ng)

        if CONF.use_neutron:
            res_type = "OS::Neutron::SecurityGroup"
            desc_key = "description"
            rules_key = "rules"
            create_rule = lambda ip_version, cidr, proto, from_port, to_port: {
                "ethertype": "IPv{}".format(ip_version),
                "remote_ip_prefix": cidr,
                "protocol": proto,
                "port_range_min": six.text_type(from_port),
                "port_range_max": six.text_type(to_port)}
        else:
            res_type = "AWS::EC2::SecurityGroup"
            desc_key = "GroupDescription"
            rules_key = "SecurityGroupIngress"
            create_rule = lambda _, cidr, proto, from_port, to_port: {
                "CidrIp": cidr,
                "IpProtocol": proto,
                "FromPort": six.text_type(from_port),
                "ToPort": six.text_type(to_port)}

        rules = self._serialize_auto_security_group_rules(ng, create_rule)

        return {
            security_group_name: {
                "type": res_type,
                "properties": {
                    desc_key: security_group_description,
                    rules_key: rules
                }
            }
        }

    def _serialize_auto_security_group_rules(self, ng, create_rule):
        rules = []
        for port in ng.open_ports:
            rules.append(create_rule(4, '0.0.0.0/0', 'tcp', port, port))
            rules.append(create_rule(6, '::/0', 'tcp', port, port))

        rules.append(create_rule(4, '0.0.0.0/0', 'tcp', SSH_PORT, SSH_PORT))
        rules.append(create_rule(6, '::/0', 'tcp', SSH_PORT, SSH_PORT))

        # open all traffic for private networks
        if CONF.use_neutron:
            for cidr in neutron.get_private_network_cidrs(ng.cluster):
                ip_ver = 6 if ':' in cidr else 4
                for protocol in ['tcp', 'udp']:
                    rules.append(create_rule(ip_ver, cidr, protocol, 1, 65535))
                rules.append(create_rule(ip_ver, cidr, 'icmp', 0, 255))

        return rules

    @staticmethod
    def _get_wait_condition_timeout(ng):
        configs = ng.cluster.cluster_configs
        timeout_cfg = plugin_provisioning.HEAT_WAIT_CONDITION_TIMEOUT
        cfg_target = timeout_cfg.applicable_target
        cfg_name = timeout_cfg.name
        return int(configs.get(cfg_target,
                               {}).get(cfg_name, timeout_cfg.default_value))

    def _serialize_instance(self, ng):
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

            properties["networks"] = [{"port": {"get_resource": "port"}}]

            if ng.floating_ip_pool:
                resources.update(self._serialize_neutron_floating(ng))
        else:
            if ng.floating_ip_pool:
                resources.update(self._serialize_nova_floating(ng))

            if ng.security_groups or ng.auto_security_group:
                properties["security_groups"] = self._get_security_groups(ng)

        # Check if cluster contains user key-pair and include it to template.
        if self.cluster.user_keypair_id:
            properties["key_name"] = self.cluster.user_keypair_id

        gen_userdata_func = self.node_groups_extra[ng.id]['gen_userdata_func']
        key_script = gen_userdata_func(ng, inst_name)
        if CONF.heat_enable_wait_condition:
            wait_condition_script = (
                "wc_notify --data-binary '{\"status\": \"SUCCESS\"}'")
            userdata = {
                "str_replace": {
                    "template": "\n".join(
                        [key_script, wait_condition_script]),
                    "params": {
                        "wc_notify": {
                            "get_attr": [
                                _get_wc_handle_name(ng.name),
                                "curl_cli"
                            ]
                        }
                    }
                }
            }
        else:
            userdata = key_script

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
            INSTANCE_RESOURCE_NAME: {
                "type": "OS::Nova::Server",
                "properties": properties
            }
        })

        resources.update(self._serialize_volume(ng))
        resources.update(self._serialize_wait_condition(ng))
        return resources

    def _serialize_wait_condition(self, ng):
        if not CONF.heat_enable_wait_condition:
            return {}
        return {
            _get_wc_handle_name(ng.name): {
                "type": "OS::Heat::WaitConditionHandle"
            },
            _get_wc_waiter_name(ng.name): {
                "type": "OS::Heat::WaitCondition",
                "depends_on": INSTANCE_RESOURCE_NAME,
                "properties": {
                    "timeout": self._get_wait_condition_timeout(ng),
                    "handle": {"get_resource": _get_wc_handle_name(ng.name)}
                }
            }
        }

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
                    "port_id": {"get_resource": "port"}
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
                    "floating_ip": {"get_resource": "floating_ip"},
                    "server_id": {"get_resource": INSTANCE_RESOURCE_NAME}
                }
            }
        }

    def _serialize_volume(self, ng):
        if not ng.volumes_size or not ng.volumes_per_node:
            return {}
        volume_file_name = "file://" + ng.name + "-volume.yaml"
        self.files[volume_file_name] = self._serialize_volume_file(ng)

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
                            "instance": {"get_resource":
                                         INSTANCE_RESOURCE_NAME}}
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
            "description": self._volume_for_node_group_description(ng),
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
                        "volume_id": {"get_resource": "volume"},
                    }
                }},
            "outputs": {}
        })

    def _get_security_groups(self, node_group):
        node_group_sg = list(node_group.security_groups or [])
        if node_group.auto_security_group:
            node_group_sg += [
                {"get_resource": g.generate_auto_security_group_name(
                    node_group)}
            ]
        return node_group_sg

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
        cluster = node_group.cluster
        outputs = h.get_stack_outputs(cluster)
        for output in outputs:
            if output['output_key'] == node_group.name + "-instances":
                return output["output_value"]

        return []
