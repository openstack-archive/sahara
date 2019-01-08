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

import copy

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils as json
import six
import yaml

from sahara.plugins import provisioning as plugin_provisioning
from sahara.service.heat import commons as heat_common
from sahara.utils import cluster as cl
from sahara.utils import general as g
from sahara.utils.openstack import base as b
from sahara.utils.openstack import heat as h
from sahara.utils.openstack import neutron
from sahara.utils.openstack import nova

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

SSH_PORT = 22
INSTANCE_RESOURCE_NAME = "inst"
SERVER_GROUP_NAMES = "servgroups"
AUTO_SECURITY_GROUP_PARAM_NAME = "autosecgroup"
INTERNAL_DESIGNATE_REC = "internal_designate_record"
INTERNAL_DESIGNATE_REV_REC = "internal_designate_reverse_record"
EXTERNAL_DESIGNATE_REC = "external_designate_record"
EXTERNAL_DESIGNATE_REV_REC = "external_designate_reverse_record"

# TODO(vgridnev): Using insecure flag until correct way to pass certificate
# will be invented
WAIT_CONDITION_SCRIPT_TEMPLATE = '''
while true; do
    wc_notify --insecure --data-binary '{"status": "SUCCESS"}'
    if [ $? -eq 0 ]; then
        break
    fi
    sleep 10
done
'''

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


def _get_inst_domain_name(domain):
    return {
        "list_join": [
            '.',
            [{"get_attr": [INSTANCE_RESOURCE_NAME, "name"]}, domain]]
    }


def _get_aa_group_name(cluster, server_group_index):
    return g.generate_aa_group_name(cluster.name, server_group_index)


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


def _get_index_from_inst_name(inst_name):
    return inst_name.split('-')[-1]


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
        self._current_sg_index = 1

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
                             gen_userdata_func, instances_to_delete=None):
        self.node_groups_extra[node_group_id] = {
            'node_count': node_count,
            'gen_userdata_func': gen_userdata_func,
            'instances_to_delete': instances_to_delete
        }

    def _get_main_template(self, instances_to_delete=None):
        outputs = {}
        resources = self._serialize_resources(outputs, instances_to_delete)
        return yaml.safe_dump({
            "heat_template_version": heat_common.HEAT_TEMPLATE_VERSION,
            "description": self.base_info,
            "resources": resources,
            "outputs": outputs
        })

    def instantiate(self, update_existing, disable_rollback=True,
                    instances_to_delete=None):
        main_tmpl = self._get_main_template(instances_to_delete)
        kwargs = {
            'stack_name': self.cluster.stack_name,
            'timeout_mins': 180,
            'disable_rollback': disable_rollback,
            'parameters': {},
            'template': main_tmpl,
            'files': self.files
        }

        if CONF.heat_stack_tags:
            kwargs['tags'] = ",".join(CONF.heat_stack_tags)

        log_kwargs = copy.deepcopy(kwargs)
        log_kwargs['template'] = yaml.safe_load(log_kwargs['template'])
        for filename in log_kwargs['files'].keys():
            log_kwargs['files'][filename] = yaml.safe_load(
                log_kwargs['files'][filename])
        log_kwargs = json.dumps(log_kwargs)

        if not update_existing:
            LOG.debug("Creating Heat stack with args: \n{args}"
                      .format(args=log_kwargs))
            b.execute_with_retries(h.client().stacks.create, **kwargs)
        else:
            stack = h.get_stack(self.cluster.stack_name)
            self.last_updated_time = stack.updated_time
            LOG.debug("Updating Heat stack {stack} with args: \n"
                      "{args}".format(stack=stack, args=log_kwargs))
            b.execute_with_retries(stack.update, **kwargs)

    def _get_server_group_name(self):
        index = self._current_sg_index
        # computing server group index in round robin fashion
        if index < self.cluster.anti_affinity_ratio:
            self._current_sg_index = (index + 1)
        else:
            self._current_sg_index = 1
        return _get_aa_group_name(self.cluster, self._current_sg_index)

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
                    "get_param": [SERVER_GROUP_NAMES,
                                  {"get_param": "instance_index"}]
                }
            }
        }

    def _serialize_resources(self, outputs, instances_to_delete=None):
        resources = {}

        if self.cluster.anti_affinity:
            # Creating server groups equal to the anti_affinity_ratio
            for i in range(0, self.cluster.anti_affinity_ratio):
                resources.update(self._serialize_aa_server_group(i + 1))

        for ng in self.cluster.node_groups:
            resources.update(self._serialize_ng_group(ng, outputs,
                                                      instances_to_delete))

        for ng in self.cluster.node_groups:
            resources.update(self._serialize_auto_security_group(ng))

        return resources

    def _serialize_ng_group(self, ng, outputs, instances_to_delete=None):
        ng_file_name = "file://" + ng.name + ".yaml"
        self.files[ng_file_name] = self._serialize_ng_file(ng)

        outputs[ng.name + "-instances"] = {
            "value": {"get_attr": [ng.name, "instance"]}}
        properties = {"instance_index": "%index%"}

        if ng.cluster.anti_affinity:
            ng_count = self.node_groups_extra[ng.id]['node_count']
            # assuming instance_index also start from index 0
            for i in range(0, ng_count):
                server_group_name = self._get_server_group_name()
                server_group_resource = {
                    "get_resource": server_group_name
                }
                if SERVER_GROUP_NAMES not in properties:
                    properties[SERVER_GROUP_NAMES] = []

                properties[SERVER_GROUP_NAMES].insert(i, server_group_resource)

        if ng.auto_security_group:
            properties[AUTO_SECURITY_GROUP_PARAM_NAME] = {
                'get_resource': g.generate_auto_security_group_name(ng)}

        removal_policies = []
        if self.node_groups_extra[ng.id]['instances_to_delete']:
            resource_list = []
            for name in self.node_groups_extra[ng.id]['instances_to_delete']:
                resource_list.append(_get_index_from_inst_name(name))
            removal_policies.append({'resource_list': resource_list})

        return {
            ng.name: {
                "type": "OS::Heat::ResourceGroup",
                "properties": {
                    "count": self.node_groups_extra[ng.id]['node_count'],
                    "removal_policies": removal_policies,
                    "resource_def": {
                        "type": ng_file_name,
                        "properties": properties
                    }
                }
            }
        }

    def _serialize_ng_file(self, ng):
        parameters = {"instance_index": {"type": "string"}}

        if ng.cluster.anti_affinity:
            parameters[SERVER_GROUP_NAMES] = {"type": "comma_delimited_list",
                                              "default": []}

        if ng.auto_security_group:
            parameters[AUTO_SECURITY_GROUP_PARAM_NAME] = {'type': "string"}

        return yaml.safe_dump({
            "heat_template_version": heat_common.HEAT_TEMPLATE_VERSION,
            "description": self._node_group_description(ng),
            "parameters": parameters,
            "resources": self._serialize_instance(ng),
            "outputs": {
                "instance": {"value": {
                    "physical_id": {"get_resource": INSTANCE_RESOURCE_NAME},
                    "name": {"get_attr": [INSTANCE_RESOURCE_NAME, "name"]}
                }}}
        })

    def _serialize_auto_security_group(self, ng):
        if not ng.auto_security_group:
            return {}
        security_group_name = g.generate_auto_security_group_name(ng)
        security_group_description = self._asg_for_node_group_description(ng)

        res_type = "OS::Neutron::SecurityGroup"
        desc_key = "description"
        rules_key = "rules"
        create_rule = lambda ip_version, cidr, proto, from_port, to_port: {
            "ethertype": "IPv{}".format(ip_version),
            "remote_ip_prefix": cidr,
            "protocol": proto,
            "port_range_min": six.text_type(from_port),
            "port_range_max": six.text_type(to_port)}

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

    def _serialize_designate_records(self):
        if not self.cluster.use_designate_feature():
            return {}
        hostname = _get_inst_domain_name(self.cluster.domain_name)
        return {
            INTERNAL_DESIGNATE_REC: {
                'type': 'OS::Designate::Record',
                'properties': {
                    'name': hostname,
                    'type': 'A',
                    'data': {'get_attr': [
                        INSTANCE_RESOURCE_NAME, 'networks', 'private', 0]},
                    'domain': self.cluster.domain_name
                }
            },
            EXTERNAL_DESIGNATE_REC: {
                'type': 'OS::Designate::Record',
                'properties': {
                    'name': hostname,
                    'type': 'A',
                    'data': {'get_attr': ['floating_ip', 'ip']},
                    'domain': self.cluster.domain_name
                }
            }
        }

    def _serialize_designate_reverse_records(self):

        if not self.cluster.use_designate_feature():
            return {}

        def _generate_reversed_ip(ip):
            return {
                'list_join': [
                    '.',
                    [
                        {'str_split': ['.', ip, 3]},
                        {'str_split': ['.', ip, 2]},
                        {'str_split': ['.', ip, 1]},
                        {'str_split': ['.', ip, 0]},
                        'in-addr.arpa.'
                    ]
                ]
            }

        hostname = _get_inst_domain_name(self.cluster.domain_name)
        return {
            INTERNAL_DESIGNATE_REV_REC: {
                'type': 'OS::Designate::Record',
                'properties': {
                    'name': _generate_reversed_ip({'get_attr': [
                        INSTANCE_RESOURCE_NAME, 'networks', 'private', 0]}),
                    'type': 'PTR',
                    'data': hostname,
                    'domain': 'in-addr.arpa.'
                }
            },
            EXTERNAL_DESIGNATE_REV_REC: {
                'type': 'OS::Designate::Record',
                'properties': {
                    'name': _generate_reversed_ip(
                        {'get_attr': ['floating_ip', 'ip']}),
                    'type': 'PTR',
                    'data': hostname,
                    'domain': 'in-addr.arpa.'
                }
            }
        }

    def _serialize_instance(self, ng):
        resources = {}
        properties = {}

        inst_name = _get_inst_name(ng)
        private_net = self.cluster.neutron_management_network

        sec_groups = self._get_security_groups(ng)

        # Check if cluster contains user key-pair and include it to template.
        if self.cluster.user_keypair_id:
            properties["key_name"] = self.cluster.user_keypair_id

        port_name = _get_port_name(ng)

        resources.update(self._serialize_port(
            port_name, private_net, sec_groups))

        properties["networks"] = [{"port": {"get_resource": "port"}}]

        if ng.floating_ip_pool:
            resources.update(self._serialize_neutron_floating(ng))

        gen_userdata_func = self.node_groups_extra[ng.id]['gen_userdata_func']
        key_script = gen_userdata_func(ng, inst_name)
        if CONF.heat_enable_wait_condition:
            etc_hosts = cl.etc_hosts_entry_for_service('orchestration')
            if etc_hosts:
                etc_hosts = "echo '%s' | sudo tee -a /etc/hosts" % etc_hosts
            tml = [key_script, WAIT_CONDITION_SCRIPT_TEMPLATE]
            if etc_hosts:
                tml = [key_script, etc_hosts, WAIT_CONDITION_SCRIPT_TEMPLATE]
            userdata = {
                "str_replace": {
                    "template": "\n".join(tml),
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
            "admin_user": ng.image_username,
            "user_data": userdata
        })

        if ng.boot_from_volume:
            resources.update(self._get_bootable_volume(ng))
            properties["block_device_mapping"] = [
                {"device_name": "vda",
                 "volume_id": {"get_resource": "bootable_volume"},
                 "delete_on_termination": "true"}]

        else:
            properties.update({"image": ng.get_image_id()})

        resources.update({
            INSTANCE_RESOURCE_NAME: {
                "type": "OS::Nova::Server",
                "properties": properties
            }
        })

        resources.update(self._serialize_designate_records())
        resources.update(self._serialize_designate_reverse_records())
        resources.update(self._serialize_volume(ng))
        resources.update(self._serialize_wait_condition(ng))
        return resources

    def _get_bootable_volume(self, node_group):
        node_group_flavor = nova.get_flavor(id=node_group.flavor_id)
        image_size = node_group_flavor.disk

        properties = {}
        properties["size"] = image_size
        properties["image"] = node_group.get_image_id()

        if node_group.boot_volume_type:
            properties["volume_type"] = node_group.boot_volume_type

        if node_group.boot_volume_availability_zone:
            properties["availability_zone"] = (
                node_group.boot_volume_availability_zone
            )

        if node_group.boot_volume_local_to_instance:
            properties["scheduler_hints"] = {
                "local_to_instance": {"get_param": "instance"}}

        return {
            "bootable_volume": {
                "type": "OS::Cinder::Volume",
                "properties": properties
            }
        }

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
            "heat_template_version": heat_common.HEAT_TEMPLATE_VERSION,
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
                {"get_param": AUTO_SECURITY_GROUP_PARAM_NAME}
            ]
        return node_group_sg

    def _serialize_aa_server_group(self, server_group_index):
        server_group_name = _get_aa_group_name(self.cluster,
                                               server_group_index)
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
