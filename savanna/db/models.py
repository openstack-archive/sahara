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

import sqlalchemy as sa
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship

from savanna.db import model_base as mb
from savanna.utils import configs
from savanna.utils import crypto
from savanna.utils.openstack import nova
from savanna.utils import remote
from savanna.utils import sqlatypes as st


class Cluster(mb.SavannaBase, mb.IdMixin, mb.TenantMixin,
              mb.PluginSpecificMixin, mb.ExtraMixin):
    """Contains all info about cluster."""

    __filter_cols__ = ['private_key']
    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    name = sa.Column(sa.String(80), nullable=False)
    default_image_id = sa.Column(sa.String(36))
    cluster_configs = sa.Column(st.JsonDictType())
    node_groups = relationship('NodeGroup', cascade="all,delete",
                               backref='cluster')
    # TODO(slukjanov): replace String type with sa.Enum(*CLUSTER_STATUSES)
    status = sa.Column(sa.String(80))
    status_description = sa.Column(sa.String(200))
    private_key = sa.Column(sa.Text, default=crypto.generate_private_key())
    user_keypair_id = sa.Column(sa.String(80))
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('ClusterTemplate.id'))
    cluster_template = relationship('ClusterTemplate',
                                    backref="clusters")

    def __init__(self, name, tenant_id, plugin_name, hadoop_version,
                 default_image_id=None, cluster_configs=None,
                 cluster_template_id=None, user_keypair_id=None):
        self.name = name
        self.tenant_id = tenant_id
        self.plugin_name = plugin_name
        self.hadoop_version = hadoop_version
        self.default_image_id = default_image_id
        self.cluster_configs = cluster_configs or {}
        self.cluster_template_id = cluster_template_id
        self.user_keypair_id = user_keypair_id

    def to_dict(self):
        d = super(Cluster, self).to_dict()
        d['node_groups'] = [ng.dict for ng in self.node_groups]
        return d

    @property
    def user_keypair(self):
        """Extract user keypair object from nova.

        It contains 'public_key' and 'fingerprint' fields.
        """
        if not hasattr(self, '_user_kp'):
            self._user_kp = nova.client().keypairs.get(self.user_keypair_id)
        return self._user_kp


class NodeGroup(mb.SavannaBase, mb.IdMixin, mb.ExtraMixin):
    """Specifies group of nodes within a cluster."""

    __filter_cols__ = ['cluster_id']
    __table_args__ = (
        sa.UniqueConstraint('name', 'cluster_id'),
    )

    cluster_id = sa.Column(sa.String(36), sa.ForeignKey('Cluster.id'))
    name = sa.Column(sa.String(80), nullable=False)
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    anti_affinity_group = sa.Column(sa.String(36))
    count = sa.Column(sa.Integer, nullable=False)
    instances = relationship('Instance', cascade="all,delete",
                             backref='node_group')
    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'NodeGroupTemplate.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="node_groups")

    def __init__(self, name, flavor_id, node_processes, count, image_id=None,
                 node_configs=None, anti_affinity_group=None,
                 node_group_template_id=None):
        self.name = name
        self.flavor_id = flavor_id
        self.image_id = image_id
        self.node_processes = node_processes
        self.count = count
        self.node_configs = node_configs or {}
        self.anti_affinity_group = anti_affinity_group
        self.node_group_template_id = node_group_template_id

    def get_image_id(self):
        return self.image_id or self.cluster.default_image_id

    @property
    def username(self):
        if not hasattr(self, '_username'):
            image_id = self.get_image_id()
            self._username = nova.client().images.get(image_id).username
        return self._username

    @property
    def configuration(self):
        if hasattr(self, '_all_configs'):
            return self._all_configs

        self._all_configs = configs.merge_configs(
            self.cluster.cluster_configs,
            self.node_configs
        )

        return self._all_configs

    def to_dict(self):
        d = super(NodeGroup, self).to_dict()
        d['instances'] = [i.dict for i in self.instances]

        return d


class Instance(mb.SavannaBase, mb.ExtraMixin):
    """An OpenStack instance created for the cluster."""

    __filter_cols__ = ['node_group_id']
    __table_args__ = (
        sa.UniqueConstraint('instance_id', 'node_group_id'),
    )

    node_group_id = sa.Column(sa.String(36), sa.ForeignKey('NodeGroup.id'))
    instance_id = sa.Column(sa.String(36), primary_key=True)
    instance_name = sa.Column(sa.String(80), nullable=False)
    management_ip = sa.Column(sa.String(15))

    def __init__(self, node_group_id, instance_id, instance_name,
                 management_ip=None):
        self.node_group_id = node_group_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.management_ip = management_ip

    @property
    def nova_info(self):
        """Returns info from nova about instance."""
        return nova.client().servers.get(self.instance_id)

    @property
    def username(self):
        return self.node_group.username

    @property
    def hostname(self):
        return self.instance_name

    @property
    def remote(self):
        return remote.InstanceInteropHelper(self)


class ClusterTemplate(mb.SavannaBase, mb.IdMixin, mb.TenantMixin,
                      mb.PluginSpecificMixin):
    """Template for Cluster."""

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.String(200))
    cluster_configs = sa.Column(st.JsonDictType())

    # TODO(slukjanov): add node_groups_suggestion helper

    def __init__(self, name, tenant_id, plugin_name, hadoop_version,
                 cluster_configs=None, description=None):
        self.name = name
        self.tenant_id = tenant_id
        self.plugin_name = plugin_name
        self.hadoop_version = hadoop_version
        self.cluster_configs = cluster_configs or {}
        self.description = description

    def add_node_group_template(self, kwargs):
        relation = TemplatesRelation(self.id, **kwargs)
        self.templates_relations.append(relation)
        return relation

    def to_dict(self):
        d = super(ClusterTemplate, self).to_dict()
        d['node_groups'] = [tr.dict for tr in
                            self.templates_relations]
        return d


class NodeGroupTemplate(mb.SavannaBase, mb.IdMixin, mb.TenantMixin,
                        mb.PluginSpecificMixin):
    """Template for NodeGroup."""

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.String(200))
    flavor_id = sa.Column(sa.String(36), nullable=False)
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())

    def __init__(self, name, tenant_id, flavor_id, plugin_name,
                 hadoop_version, node_processes, node_configs=None,
                 description=None):
        self.name = name
        self.tenant_id = tenant_id
        self.flavor_id = flavor_id
        self.plugin_name = plugin_name
        self.hadoop_version = hadoop_version
        self.node_processes = node_processes
        self.node_configs = node_configs or {}
        self.description = description

    def to_object(self, values, cls, additional_values=None):
        additional_values = additional_values or {}
        return cls(
            name=values.get('name') or self.name,
            flavor_id=values.get('flavor_id') or self.flavor_id,
            node_processes=values.get('node_processes') or self.node_processes,
            count=values.get('count') or self.count,
            node_configs=configs.merge_configs(self.node_configs,
                                               values.get('node_configs')),
            node_group_template_id=self.id, **additional_values)


# TODO(slukjanov): it should be replaced with NodeGroup-based relation
class TemplatesRelation(mb.SavannaBase, mb.IdMixin):
    """NodeGroupTemplate - ClusterTemplate relationship."""

    __filter_cols__ = ['cluster_template_id', 'created', 'updated', 'id']

    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('ClusterTemplate.id'))
    cluster_template = relationship(ClusterTemplate,
                                    backref='templates_relations')

    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey('NodeGroupTemplate.id'))
    node_group_template = relationship(NodeGroupTemplate,
                                       backref='templates_relations')

    name = sa.Column(sa.String(80), nullable=False)
    flavor_id = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    count = sa.Column(sa.Integer)

    def __init__(self, cluster_template_id, name, count,
                 node_processes=None, flavor_id=None, node_configs=None,
                 node_group_template_id=None):
        self.cluster_template_id = cluster_template_id
        self.node_group_template_id = node_group_template_id
        self.name = name
        self.flavor_id = flavor_id
        self.node_processes = node_processes
        self.node_configs = node_configs or {}
        self.count = count


ClusterTemplate.node_group_templates = association_proxy("templates_relations",
                                                         "node_group_template")
NodeGroupTemplate.cluster_templates = association_proxy("templates_relations",
                                                        "cluster_template")
