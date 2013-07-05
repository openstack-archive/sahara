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

from novaclient import exceptions as nova_ex
from oslo.config import cfg
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from savanna.db import model_base as mb
from savanna.utils import configs
from savanna.utils import crypto
from savanna.utils.openstack import nova
from savanna.utils import remote
from savanna.utils import sqlatypes as st


CONF = cfg.CONF
CONF.import_opt('node_domain', 'savanna.service.networks')


## Base mixins for clusters, node groups and their templates

class NodeGroupMixin(mb.IdMixin):
    """Base NodeGroup mixin, add it to subclass is smth like node group."""

    name = sa.Column(sa.String(80), nullable=False)
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    volumes_per_node = sa.Column(sa.Integer)
    volumes_size = sa.Column(sa.Integer)
    volume_mount_prefix = sa.Column(sa.String(80))


class ClusterMixin(mb.IdMixin, mb.TenantMixin,
                   mb.PluginSpecificMixin, mb.ExtraMixin, mb.DescriptionMixin):
    """Base Cluster mixin, add it to subclass is like cluster object."""

    name = sa.Column(sa.String(80), nullable=False)
    cluster_configs = sa.Column(st.JsonDictType())
    default_image_id = sa.Column(sa.String(36))
    anti_affinity = sa.Column(st.JsonListType())


## Main objects: Cluster, NodeGroup, Instance

class Cluster(mb.SavannaBase, ClusterMixin):
    """Contains all info about cluster."""

    __filter_cols__ = ['private_key']

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    status = sa.Column(sa.String(80))
    status_description = sa.Column(sa.String(200))

    private_key = sa.Column(sa.Text, default=crypto.generate_private_key())
    user_keypair_id = sa.Column(sa.String(80))

    node_groups = relationship('NodeGroup', cascade="all,delete",
                               backref='cluster')

    info = sa.Column(st.JsonDictType())

    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('ClusterTemplate.id'))
    cluster_template = relationship('ClusterTemplate',
                                    backref="clusters")

    def __init__(self, name, tenant_id, plugin_name, hadoop_version,
                 default_image_id=None, cluster_configs=None,
                 cluster_template_id=None, user_keypair_id=None,
                 anti_affinity=None, description=None):
        self.name = name
        self.tenant_id = tenant_id
        self.plugin_name = plugin_name
        self.hadoop_version = hadoop_version
        self.default_image_id = default_image_id
        self.cluster_configs = cluster_configs or {}
        self.cluster_template_id = cluster_template_id
        self.user_keypair_id = user_keypair_id
        self.anti_affinity = anti_affinity or []
        self.description = description
        self.info = {}

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
            try:
                self._user_kp = nova.client().keypairs.get(
                    self.user_keypair_id)
            except nova_ex.NotFound:
                self._user_kp = None
        return self._user_kp


class NodeGroup(mb.SavannaBase, NodeGroupMixin):
    """Specifies group of nodes within a cluster."""

    __filter_cols__ = ['id', 'cluster_id']

    __table_args__ = (
        sa.UniqueConstraint('name', 'cluster_id'),
    )

    count = sa.Column(sa.Integer, nullable=False)
    instances = relationship('Instance', cascade="all,delete",
                             backref='node_group')

    cluster_id = sa.Column(sa.String(36), sa.ForeignKey('Cluster.id'))

    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'NodeGroupTemplate.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="node_groups")

    def __init__(self, name, flavor_id, node_processes, count, image_id=None,
                 node_configs=None, volumes_per_node=0, volumes_size=10,
                 volume_mount_prefix='/volumes/disk',
                 node_group_template_id=None):
        self.name = name
        self.flavor_id = flavor_id
        self.image_id = image_id
        self.node_processes = node_processes
        self.node_configs = node_configs or {}
        self.volumes_per_node = volumes_per_node
        self.volumes_size = volumes_size
        self.volume_mount_prefix = volume_mount_prefix

        self.node_group_template_id = node_group_template_id
        self.count = count

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

    @property
    def storage_paths(self):
        mp = []
        for idx in xrange(1, self.volumes_per_node + 1):
            mp.append(self.volume_mount_prefix + str(idx))

        # Here we assume that NG will use ephemeral drive if no volumes
        if not mp:
            mp = ['/mnt']

        return mp

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
    internal_ip = sa.Column(sa.String(15))
    management_ip = sa.Column(sa.String(15))
    volumes = sa.Column(st.JsonListType())

    def __init__(self, node_group_id, instance_id, instance_name,
                 volumes=None):
        self.node_group_id = node_group_id
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.volumes = volumes or []

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
    def fqdn(self):
        return self.instance_name + '.' + CONF.node_domain

    @property
    def remote(self):
        return remote.InstanceInteropHelper(self)


## Template objects: ClusterTemplate, NodeGroupTemplate, TemplatesRelation

class ClusterTemplate(mb.SavannaBase, ClusterMixin):
    """Template for Cluster."""

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    node_groups = relationship('TemplatesRelation', cascade="all,delete",
                               backref='cluster_template')

    def __init__(self, name, tenant_id, plugin_name, hadoop_version,
                 default_image_id=None, cluster_configs=None,
                 description=None, anti_affinity=None):
        self.name = name
        self.tenant_id = tenant_id
        self.plugin_name = plugin_name
        self.hadoop_version = hadoop_version
        self.default_image_id = default_image_id
        self.cluster_configs = cluster_configs or {}
        self.anti_affinity = anti_affinity or []
        self.description = description

    def to_dict(self):
        d = super(ClusterTemplate, self).to_dict()
        d['node_groups'] = [tr.dict for tr in
                            self.node_groups]
        return d

    def to_cluster(self, values):
        return Cluster(
            name=values.pop('name', None) or self.name,
            tenant_id=values.pop('tenant_id'),
            plugin_name=values.pop('plugin_name', None) or self.plugin_name,
            hadoop_version=(values.pop('hadoop_version', None)
                            or self.hadoop_version),
            default_image_id=(values.pop('default_image_id')
                              or self.default_image_id),
            cluster_configs=configs.merge_configs(
                self.cluster_configs, values.pop('cluster_configs', None)),
            cluster_template_id=self.id,
            anti_affinity=(values.pop('anti_affinity', None)
                           or self.anti_affinity),
            description=values.pop('description', None),
            **values)


class NodeGroupTemplate(mb.SavannaBase, mb.TenantMixin, mb.PluginSpecificMixin,
                        NodeGroupMixin, mb.DescriptionMixin):
    """Template for NodeGroup."""

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    def __init__(self, name, tenant_id, flavor_id, plugin_name, hadoop_version,
                 node_processes, image_id=None, node_configs=None,
                 volumes_per_node=0, volumes_size=10,
                 volume_mount_prefix='/volumes/disk', description=None):
        self.name = name
        self.flavor_id = flavor_id
        self.image_id = image_id
        self.node_processes = node_processes
        self.node_configs = node_configs or {}
        self.volumes_per_node = volumes_per_node
        self.volumes_size = volumes_size
        self.volume_mount_prefix = volume_mount_prefix

        self.tenant_id = tenant_id
        self.plugin_name = plugin_name
        self.hadoop_version = hadoop_version
        self.description = description

    def to_object(self, values, cls):
        values.pop('node_group_template_id', None)
        return cls(
            name=values.pop('name', None) or self.name,
            flavor_id=values.pop('flavor_id', None) or self.flavor_id,
            image_id=values.pop('image_id', None) or self.image_id,
            node_processes=(values.pop('node_processes', None)
                            or self.node_processes),
            node_configs=configs.merge_configs(
                self.node_configs, values.pop('node_configs', None)),
            volumes_per_node=(values.pop('volumes_per_node', None)
                              or self.volumes_per_node),
            volumes_size=(values.pop('volumes_size', None)
                          or self.volumes_size),
            volume_mount_prefix=(values.pop('volume_mount_prefix', None)
                                 or self.volume_mount_prefix),
            node_group_template_id=self.id, **values)


class TemplatesRelation(mb.SavannaBase, NodeGroupMixin):
    """NodeGroupTemplate - ClusterTemplate relationship.

    In fact, it's a template of NodeGroup in Cluster.
    """

    __filter_cols__ = ['cluster_template_id', 'created', 'updated', 'id']

    count = sa.Column(sa.Integer, nullable=False)

    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('ClusterTemplate.id'))

    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'NodeGroupTemplate.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="templates_relations")

    def __init__(self, name, flavor_id, node_processes, count, image_id=None,
                 node_configs=None, volumes_per_node=0, volumes_size=10,
                 volume_mount_prefix='/volumes/disk',
                 node_group_template_id=None):
        self.name = name
        self.flavor_id = flavor_id
        self.image_id = image_id
        self.node_processes = node_processes
        self.node_configs = node_configs or {}
        self.volumes_per_node = volumes_per_node
        self.volumes_size = volumes_size
        self.volume_mount_prefix = volume_mount_prefix

        self.node_group_template_id = node_group_template_id
        self.count = count
