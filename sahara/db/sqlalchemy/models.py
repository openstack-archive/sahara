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

import uuid

import six
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sahara.db.sqlalchemy import model_base as mb
from sahara.db.sqlalchemy import types as st


# Helpers

def _generate_unicode_uuid():
    return six.text_type(uuid.uuid4())


def _id_column():
    return sa.Column(sa.String(36),
                     primary_key=True,
                     default=_generate_unicode_uuid)


# Main objects: Cluster, NodeGroup, Instance

class Cluster(mb.SaharaBase):
    """Contains all info about cluster."""

    __tablename__ = 'clusters'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text)
    tenant_id = sa.Column(sa.String(36))
    trust_id = sa.Column(sa.String(36))
    is_transient = sa.Column(sa.Boolean, default=False)
    plugin_name = sa.Column(sa.String(80), nullable=False)
    hadoop_version = sa.Column(sa.String(80), nullable=False)
    cluster_configs = sa.Column(st.JsonDictType())
    default_image_id = sa.Column(sa.String(36))
    neutron_management_network = sa.Column(sa.String(36))
    anti_affinity = sa.Column(st.JsonListType())
    management_private_key = sa.Column(sa.Text, nullable=False)
    management_public_key = sa.Column(sa.Text, nullable=False)
    user_keypair_id = sa.Column(sa.String(80))
    status = sa.Column(sa.String(80))
    status_description = sa.Column(st.LongText())
    info = sa.Column(st.JsonDictType())
    extra = sa.Column(st.JsonDictType())
    rollback_info = sa.Column(st.JsonDictType())
    sahara_info = sa.Column(st.JsonDictType())
    provision_progress = relationship('ClusterProvisionStep',
                                      cascade="all,delete",
                                      backref='cluster',
                                      lazy='joined')
    node_groups = relationship('NodeGroup', cascade="all,delete",
                               backref='cluster', lazy='joined')
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('cluster_templates.id'))
    cluster_template = relationship('ClusterTemplate',
                                    backref="clusters", lazy='joined')

    def to_dict(self, show_progress=False):
        d = super(Cluster, self).to_dict()
        d['node_groups'] = [ng.to_dict() for ng in self.node_groups]
        d['provision_progress'] = [pp.to_dict(show_progress) for pp in
                                   self.provision_progress]
        return d


class NodeGroup(mb.SaharaBase):
    """Specifies group of nodes within a cluster."""

    __tablename__ = 'node_groups'

    __table_args__ = (
        sa.UniqueConstraint('name', 'cluster_id'),
    )

    id = _id_column()
    name = sa.Column(sa.String(80), nullable=False)
    tenant_id = sa.Column(sa.String(36))
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    image_username = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    volumes_per_node = sa.Column(sa.Integer)
    volumes_size = sa.Column(sa.Integer)
    volumes_availability_zone = sa.Column(sa.String(255))
    volume_mount_prefix = sa.Column(sa.String(80))
    volume_type = sa.Column(sa.String(255))
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
    floating_ip_pool = sa.Column(sa.String(36))
    security_groups = sa.Column(st.JsonListType())
    auto_security_group = sa.Column(sa.Boolean())
    availability_zone = sa.Column(sa.String(255))
    open_ports = sa.Column(st.JsonListType())
    is_proxy_gateway = sa.Column(sa.Boolean())
    volume_local_to_instance = sa.Column(sa.Boolean())

    def to_dict(self):
        d = super(NodeGroup, self).to_dict()
        d['instances'] = [i.to_dict() for i in self.instances]

        return d


class Instance(mb.SaharaBase):
    """An OpenStack instance created for the cluster."""

    __tablename__ = 'instances'

    __table_args__ = (
        sa.UniqueConstraint('instance_id', 'node_group_id'),
    )

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    node_group_id = sa.Column(sa.String(36), sa.ForeignKey('node_groups.id'))
    instance_id = sa.Column(sa.String(36))
    instance_name = sa.Column(sa.String(80), nullable=False)
    internal_ip = sa.Column(sa.String(15))
    management_ip = sa.Column(sa.String(15))
    volumes = sa.Column(st.JsonListType())


# Template objects: ClusterTemplate, NodeGroupTemplate, TemplatesRelation

class ClusterTemplate(mb.SaharaBase):
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
    neutron_management_network = sa.Column(sa.String(36))
    plugin_name = sa.Column(sa.String(80), nullable=False)
    hadoop_version = sa.Column(sa.String(80), nullable=False)
    node_groups = relationship('TemplatesRelation', cascade="all,delete",
                               backref='cluster_template', lazy='joined')
    is_default = sa.Column(sa.Boolean(), default=False)

    def to_dict(self):
        d = super(ClusterTemplate, self).to_dict()
        d['node_groups'] = [tr.to_dict() for tr in
                            self.node_groups]
        return d


class NodeGroupTemplate(mb.SaharaBase):
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
    volumes_per_node = sa.Column(sa.Integer, nullable=False)
    volumes_size = sa.Column(sa.Integer)
    volumes_availability_zone = sa.Column(sa.String(255))
    volume_mount_prefix = sa.Column(sa.String(80))
    volume_type = sa.Column(sa.String(255))
    floating_ip_pool = sa.Column(sa.String(36))
    security_groups = sa.Column(st.JsonListType())
    auto_security_group = sa.Column(sa.Boolean())
    availability_zone = sa.Column(sa.String(255))
    is_proxy_gateway = sa.Column(sa.Boolean())
    volume_local_to_instance = sa.Column(sa.Boolean())
    is_default = sa.Column(sa.Boolean(), default=False)


class TemplatesRelation(mb.SaharaBase):
    """NodeGroupTemplate - ClusterTemplate relationship.

    In fact, it's a template of NodeGroup in Cluster.
    """

    __tablename__ = 'templates_relations'

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(80), nullable=False)
    flavor_id = sa.Column(sa.String(36), nullable=False)
    image_id = sa.Column(sa.String(36))
    node_processes = sa.Column(st.JsonListType())
    node_configs = sa.Column(st.JsonDictType())
    volumes_per_node = sa.Column(sa.Integer)
    volumes_size = sa.Column(sa.Integer)
    volumes_availability_zone = sa.Column(sa.String(255))
    volume_mount_prefix = sa.Column(sa.String(80))
    volume_type = sa.Column(sa.String(255))
    count = sa.Column(sa.Integer, nullable=False)
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('cluster_templates.id'))
    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'node_group_templates.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="templates_relations",
                                       lazy='joined')
    floating_ip_pool = sa.Column(sa.String(36))
    security_groups = sa.Column(st.JsonListType())
    auto_security_group = sa.Column(sa.Boolean())
    availability_zone = sa.Column(sa.String(255))
    is_proxy_gateway = sa.Column(sa.Boolean())
    volume_local_to_instance = sa.Column(sa.Boolean())


# EDP objects: DataSource, Job, Job Execution, JobBinary

class DataSource(mb.SaharaBase):
    """DataSource - represent a diffident types of data sources.

    e.g. Swift, Cassandra etc.
    """

    __tablename__ = 'data_sources'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text())
    type = sa.Column(sa.String(80), nullable=False)
    url = sa.Column(sa.String(256), nullable=False)
    credentials = sa.Column(st.JsonDictType())


class JobExecution(mb.SaharaBase):
    """JobExecution - represent a job execution of specific cluster."""

    __tablename__ = 'job_executions'

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    job_id = sa.Column(sa.String(36),
                       sa.ForeignKey('jobs.id'))
    input_id = sa.Column(sa.String(36),
                         sa.ForeignKey('data_sources.id'))
    output_id = sa.Column(sa.String(36),
                          sa.ForeignKey('data_sources.id'))
    start_time = sa.Column(sa.DateTime())
    end_time = sa.Column(sa.DateTime())
    cluster_id = sa.Column(sa.String(36),
                           sa.ForeignKey('clusters.id'))
    info = sa.Column(st.JsonDictType())
    oozie_job_id = sa.Column(sa.String(100))
    return_code = sa.Column(sa.String(80))
    job_configs = sa.Column(st.JsonDictType())
    extra = sa.Column(st.JsonDictType())

mains_association = sa.Table("mains_association",
                             mb.SaharaBase.metadata,
                             sa.Column("Job_id",
                                       sa.String(36),
                                       sa.ForeignKey("jobs.id")),
                             sa.Column("JobBinary_id",
                                       sa.String(36),
                                       sa.ForeignKey("job_binaries.id"))
                             )


libs_association = sa.Table("libs_association",
                            mb.SaharaBase.metadata,
                            sa.Column("Job_id",
                                      sa.String(36),
                                      sa.ForeignKey("jobs.id")),
                            sa.Column("JobBinary_id",
                                      sa.String(36),
                                      sa.ForeignKey("job_binaries.id"))
                            )


class Job(mb.SaharaBase):
    """Job - description and location of a job binary."""

    __tablename__ = 'jobs'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text())
    type = sa.Column(sa.String(80), nullable=False)

    mains = relationship("JobBinary",
                         secondary=mains_association, lazy="joined")

    libs = relationship("JobBinary",
                        secondary=libs_association, lazy="joined")

    def to_dict(self):
        d = super(Job, self).to_dict()
        d['mains'] = [jb.to_dict() for jb in self.mains]
        d['libs'] = [jb.to_dict() for jb in self.libs]
        return d


class JobBinaryInternal(mb.SaharaBase):
    """JobBinaryInternal - raw binary storage for executable jobs."""

    __tablename__ = 'job_binary_internal'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(80), nullable=False)
    data = sa.orm.deferred(sa.Column(st.LargeBinary()))
    datasize = sa.Column(sa.BIGINT)


class JobBinary(mb.SaharaBase):
    """JobBinary - raw binary storage for executable jobs."""

    __tablename__ = 'job_binaries'

    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    tenant_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text())
    url = sa.Column(sa.String(256), nullable=False)
    extra = sa.Column(st.JsonDictType())


class ClusterEvent(mb.SaharaBase):
    """"Event - represent a info about current provision step."""

    __tablename__ = 'cluster_events'

    __table_args__ = (
        sa.UniqueConstraint('id', 'step_id'),
    )

    id = _id_column()
    node_group_id = sa.Column(sa.String(36))
    instance_id = sa.Column(sa.String(36))
    instance_name = sa.Column(sa.String(80))
    event_info = sa.Column(sa.Text)
    successful = sa.Column(sa.Boolean, nullable=False)
    step_id = sa.Column(sa.String(36), sa.ForeignKey(
        'cluster_provision_steps.id'))


class ClusterProvisionStep(mb.SaharaBase):
    """ProvisionStep - represent a current provision step of cluster."""

    __tablename__ = 'cluster_provision_steps'

    __table_args__ = (
        sa.UniqueConstraint('id', 'cluster_id'),
    )

    id = _id_column()
    cluster_id = sa.Column(sa.String(36), sa.ForeignKey('clusters.id'))
    tenant_id = sa.Column(sa.String(36))
    step_name = sa.Column(sa.String(80))
    step_type = sa.Column(sa.String(36))
    completed = sa.Column(sa.Integer)
    total = sa.Column(sa.Integer)
    successful = sa.Column(sa.Boolean, nullable=True)
    started_at = sa.Column(sa.DateTime())
    completed_at = sa.Column(sa.DateTime())
    events = relationship('ClusterEvent', cascade="all,delete",
                          backref='ClusterProvisionStep',
                          lazy='joined')

    def to_dict(self, show_progress):
        d = super(ClusterProvisionStep, self).to_dict()
        if show_progress:
            d['events'] = [event.to_dict() for event in self.events]
        return d
