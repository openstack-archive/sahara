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
from sqlalchemy.orm import relationship

from savanna.db_new.sqlalchemy import model_base as mb
from savanna.db_new.sqlalchemy import types as st
from savanna.openstack.common import uuidutils
from savanna.utils import crypto


## Helpers

def _generate_unicode_uuid():
    return unicode(uuidutils.generate_uuid())


def _id_column():
    return sa.Column(sa.String(36),
                     primary_key=True,
                     default=_generate_unicode_uuid)


## Main objects: Cluster, NodeGroup, Instance

class Cluster(mb.SavannaBase):
    """Contains all info about cluster."""

    __tablename__ = 'clusters'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text)
    tenant_id = sa.Column(sa.String(36))
    plugin_name = sa.Column(sa.String(80), nullable=False)
    hadoop_version = sa.Column(sa.String(80), nullable=False)
    cluster_configs = sa.Column(st.JsonDictType())
    default_image_id = sa.Column(sa.String(36))
    anti_affinity = sa.Column(st.JsonListType())
    private_key = sa.Column(sa.Text, default=crypto.generate_private_key())
    user_keypair_id = sa.Column(sa.String(80))
    status = sa.Column(sa.String(80))
    status_description = sa.Column(sa.String(200))
    info = sa.Column(st.JsonDictType())
    node_groups = relationship('NodeGroup', cascade="all,delete",
                               backref='cluster', lazy='joined')
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('cluster_templates.id'))
    cluster_template = relationship('ClusterTemplate',
                                    backref="clusters", lazy='joined')

    def to_dict(self):
        d = super(Cluster, self).to_dict()
        d['node_groups'] = [ng.to_dict() for ng in self.node_groups]
        return d


class NodeGroup(mb.SavannaBase):
    """Specifies group of nodes within a cluster."""

    __tablename__ = 'node_groups'

    __table_args__ = (
        sa.UniqueConstraint('name', 'cluster_id'),
    )

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    volumes_per_node = sa.Column(sa.Integer)
    volumes_size = sa.Column(sa.Integer)
    volume_mount_prefix = sa.Column(sa.String(80))
    count = sa.Column(sa.Integer, nullable=False)
    instances = relationship('Instance', cascade="all,delete",
                             backref='node_group',
                             order_by="Instance.instance_name", lazy='joined')
    cluster_id = sa.Column(sa.String(36), sa.ForeignKey('clusters.id'))
    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'node_group_templates.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="node_groups", lazy='joined')

    def to_dict(self):
        d = super(NodeGroup, self).to_dict()
        d['instances'] = [i.to_dict() for i in self.instances]

        return d


class Instance(mb.SavannaBase):
    """An OpenStack instance created for the cluster."""

    __tablename__ = 'instances'

    __table_args__ = (
        sa.UniqueConstraint('instance_id', 'node_group_id'),
    )

    id = _id_column()
    node_group_id = sa.Column(sa.String(36), sa.ForeignKey('node_groups.id'))
    instance_id = sa.Column(sa.String(36))
    instance_name = sa.Column(sa.String(80), nullable=False)
    internal_ip = sa.Column(sa.String(15))
    management_ip = sa.Column(sa.String(15))
    volumes = sa.Column(st.JsonListType())


## Template objects: ClusterTemplate, NodeGroupTemplate, TemplatesRelation

class ClusterTemplate(mb.SavannaBase):
    """Template for Cluster."""

    __tablename__ = 'cluster_templates'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text)
    cluster_configs = sa.Column(st.JsonDictType())
    default_image_id = sa.Column(sa.String(36))
    anti_affinity = sa.Column(st.JsonListType())
    tenant_id = sa.Column(sa.String(36))
    plugin_name = sa.Column(sa.String(80), nullable=False)
    hadoop_version = sa.Column(sa.String(80), nullable=False)
    node_groups = relationship('TemplatesRelation', cascade="all,delete",
                               backref='cluster_template', lazy='joined')

    def to_dict(self):
        d = super(ClusterTemplate, self).to_dict()
        d['node_groups'] = [tr.to_dict() for tr in
                            self.node_groups]
        return d


class NodeGroupTemplate(mb.SavannaBase):
    """Template for NodeGroup."""

    __tablename__ = 'node_group_templates'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text)
    tenant_id = sa.Column(sa.String(36))
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    plugin_name = sa.Column(sa.String(80), nullable=False)
    hadoop_version = sa.Column(sa.String(80), nullable=False)
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    volumes_per_node = sa.Column(sa.Integer)
    volumes_size = sa.Column(sa.Integer)
    volume_mount_prefix = sa.Column(sa.String(80))


class TemplatesRelation(mb.SavannaBase):
    """NodeGroupTemplate - ClusterTemplate relationship.

    In fact, it's a template of NodeGroup in Cluster.
    """

    __tablename__ = 'templates_relations'

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    volumes_per_node = sa.Column(sa.Integer)
    volumes_size = sa.Column(sa.Integer)
    volume_mount_prefix = sa.Column(sa.String(80))
    count = sa.Column(sa.Integer, nullable=False)
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('cluster_templates.id'))
    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'node_group_templates.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="templates_relations",
                                       lazy='joined')
