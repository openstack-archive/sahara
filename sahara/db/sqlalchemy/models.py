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


from oslo_utils import uuidutils
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sahara.db.sqlalchemy import model_base as mb
from sahara.db.sqlalchemy import types as st


# Helpers

def _generate_unicode_uuid():
    return uuidutils.generate_uuid()


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
    anti_affinity_ratio = sa.Column(sa.Integer, default=1)
    management_private_key = sa.Column(sa.Text, nullable=False)
    management_public_key = sa.Column(sa.Text, nullable=False)
    user_keypair_id = sa.Column(sa.String(80))
    status = sa.Column(sa.String(80))
    status_description = sa.Column(st.LongText())
    info = sa.Column(st.JsonDictType())
    extra = sa.Column(st.JsonDictType())
    rollback_info = sa.Column(st.JsonDictType())
    sahara_info = sa.Column(st.JsonDictType())
    use_autoconfig = sa.Column(sa.Boolean(), default=True)
    provision_progress = relationship('ClusterProvisionStep',
                                      cascade="all,delete",
                                      backref='cluster',
                                      lazy='subquery')
    verification = relationship('ClusterVerification', cascade="all,delete",
                                backref="cluster", lazy='joined')
    node_groups = relationship('NodeGroup', cascade="all,delete",
                               backref='cluster', lazy='subquery')
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('cluster_templates.id'))
    cluster_template = relationship('ClusterTemplate',
                                    backref="clusters")
    shares = sa.Column(st.JsonListType())
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())
    domain_name = sa.Column(sa.String(255))

    def to_dict(self, show_progress=False):
        d = super(Cluster, self).to_dict()
        d['node_groups'] = [ng.to_dict() for ng in self.node_groups]
        d['provision_progress'] = [pp.to_dict(show_progress) for pp in
                                   self.provision_progress]
        if self.verification:
            d['verification'] = self.verification[0].to_dict()
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
    boot_from_volume = sa.Column(sa.Boolean(), default=False, nullable=False)
    boot_volume_type = sa.Column(sa.String(255))
    boot_volume_availability_zone = sa.Column(sa.String(255))
    boot_volume_local_to_instance = sa.Column(sa.Boolean())
    count = sa.Column(sa.Integer, nullable=False)
    use_autoconfig = sa.Column(sa.Boolean(), default=True)

    instances = relationship('Instance', cascade="all,delete",
                             backref='node_group',
                             order_by="Instance.instance_name",
                             lazy='subquery')
    cluster_id = sa.Column(sa.String(36), sa.ForeignKey('clusters.id'))
    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'node_group_templates.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="node_groups")
    floating_ip_pool = sa.Column(sa.String(36))
    security_groups = sa.Column(st.JsonListType())
    auto_security_group = sa.Column(sa.Boolean())
    availability_zone = sa.Column(sa.String(255))
    open_ports = sa.Column(st.JsonListType())
    is_proxy_gateway = sa.Column(sa.Boolean())
    volume_local_to_instance = sa.Column(sa.Boolean())
    shares = sa.Column(st.JsonListType())

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
    internal_ip = sa.Column(sa.String(45))
    management_ip = sa.Column(sa.String(45))
    volumes = sa.Column(st.JsonListType())
    storage_devices_number = sa.Column(sa.Integer)
    dns_hostname = sa.Column(sa.String(255))


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
                               backref='cluster_template', lazy='subquery')
    is_default = sa.Column(sa.Boolean(), default=False)
    use_autoconfig = sa.Column(sa.Boolean(), default=True)
    shares = sa.Column(st.JsonListType())
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())
    domain_name = sa.Column(sa.String(255))

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
    boot_from_volume = sa.Column(sa.Boolean(), default=False, nullable=False)
    boot_volume_type = sa.Column(sa.String(255))
    boot_volume_availability_zone = sa.Column(sa.String(255))
    boot_volume_local_to_instance = sa.Column(sa.Boolean())
    floating_ip_pool = sa.Column(sa.String(36))
    security_groups = sa.Column(st.JsonListType())
    auto_security_group = sa.Column(sa.Boolean())
    availability_zone = sa.Column(sa.String(255))
    is_proxy_gateway = sa.Column(sa.Boolean())
    volume_local_to_instance = sa.Column(sa.Boolean())
    is_default = sa.Column(sa.Boolean(), default=False)
    use_autoconfig = sa.Column(sa.Boolean(), default=True)
    shares = sa.Column(st.JsonListType())
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())


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
    boot_from_volume = sa.Column(sa.Boolean(), default=False, nullable=False)
    boot_volume_type = sa.Column(sa.String(255))
    boot_volume_availability_zone = sa.Column(sa.String(255))
    boot_volume_local_to_instance = sa.Column(sa.Boolean())
    count = sa.Column(sa.Integer, nullable=False)
    use_autoconfig = sa.Column(sa.Boolean(), default=True)
    cluster_template_id = sa.Column(sa.String(36),
                                    sa.ForeignKey('cluster_templates.id'))
    node_group_template_id = sa.Column(sa.String(36),
                                       sa.ForeignKey(
                                           'node_group_templates.id'))
    node_group_template = relationship('NodeGroupTemplate',
                                       backref="templates_relations")
    floating_ip_pool = sa.Column(sa.String(36))
    security_groups = sa.Column(st.JsonListType())
    auto_security_group = sa.Column(sa.Boolean())
    availability_zone = sa.Column(sa.String(255))
    is_proxy_gateway = sa.Column(sa.Boolean())
    volume_local_to_instance = sa.Column(sa.Boolean())
    shares = sa.Column(st.JsonListType())


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
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())


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
    engine_job_id = sa.Column(sa.String(100))
    return_code = sa.Column(sa.String(80))
    job_configs = sa.Column(st.JsonDictType())
    extra = sa.Column(st.JsonDictType())
    data_source_urls = sa.Column(st.JsonDictType())
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())

    def to_dict(self):
        d = super(JobExecution, self).to_dict()
        # The oozie_job_id filed is renamed to engine_job_id
        # to make this field more universal. But, we need to
        # carry both engine_job_id and oozie_job_id until we
        # can deprecate "oozie_job_id".
        d['oozie_job_id'] = self.engine_job_id

        return d


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
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())

    mains = relationship("JobBinary",
                         secondary=mains_association, lazy="subquery")

    libs = relationship("JobBinary",
                        secondary=libs_association, lazy="subquery")

    interface = relationship('JobInterfaceArgument',
                             cascade="all,delete",
                             order_by="JobInterfaceArgument.order",
                             backref='job',
                             lazy='subquery')

    def to_dict(self):
        d = super(Job, self).to_dict()
        d['mains'] = [jb.to_dict() for jb in self.mains]
        d['libs'] = [jb.to_dict() for jb in self.libs]
        d['interface'] = [arg.to_dict() for arg in self.interface]
        return d


class JobInterfaceArgument(mb.SaharaBase):
    """JobInterfaceArgument - Configuration setting for a specific job."""

    __tablename__ = 'job_interface_arguments'

    __table_args__ = (
        sa.UniqueConstraint('job_id', 'name'),
        sa.UniqueConstraint('job_id', 'order')
    )

    id = _id_column()
    job_id = sa.Column(sa.String(36), sa.ForeignKey('jobs.id'),
                       nullable=False)
    tenant_id = sa.Column(sa.String(36))
    name = sa.Column(sa.String(80), nullable=False)
    description = sa.Column(sa.Text())
    mapping_type = sa.Column(sa.String(80), nullable=False)
    location = sa.Column(sa.Text(), nullable=False)
    value_type = sa.Column(sa.String(80), nullable=False)
    required = sa.Column(sa.Boolean(), nullable=False)
    order = sa.Column(sa.SmallInteger(), nullable=False)
    default = sa.Column(sa.Text())


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
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())


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
    is_public = sa.Column(sa.Boolean())
    is_protected = sa.Column(sa.Boolean())


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
    total = sa.Column(sa.Integer)
    successful = sa.Column(sa.Boolean, nullable=True)
    events = relationship('ClusterEvent', cascade="all,delete",
                          backref='ClusterProvisionStep',
                          lazy='subquery')

    def to_dict(self, show_progress):
        d = super(ClusterProvisionStep, self).to_dict()
        if show_progress:
            d['events'] = [event.to_dict() for event in self.events]
        return d


class ClusterVerification(mb.SaharaBase):
    """ClusterVerification represent results of cluster health checks."""

    __tablename__ = 'cluster_verifications'

    __table_args__ = (sa.UniqueConstraint('id', 'cluster_id'),)

    id = _id_column()
    cluster_id = sa.Column(
        sa.String(36), sa.ForeignKey('clusters.id'))
    status = sa.Column(sa.String(15))
    checks = relationship(
        'ClusterHealthCheck', cascade="all,delete",
        backref='ClusterVerification', lazy='subquery')

    def to_dict(self):
        base = super(ClusterVerification, self).to_dict()
        base['checks'] = [check.to_dict() for check in self.checks]
        return base


class ClusterHealthCheck(mb.SaharaBase):
    """ClusterHealthCheck respresent cluster health check."""

    __tablename__ = 'cluster_health_checks'
    __table_args__ = (sa.UniqueConstraint('id', 'verification_id'),)

    id = _id_column()
    verification_id = sa.Column(
        sa.String(36), sa.ForeignKey('cluster_verifications.id'))
    status = sa.Column(sa.String(15))
    description = sa.Column(sa.Text)
    name = sa.Column(sa.String(80))


class PluginData(mb.SaharaBase):
    """Plugin Data represents Provisioning Plugin."""

    __tablename__ = 'plugin_data'
    __table_args__ = (
        sa.UniqueConstraint('name', 'tenant_id'),
    )

    id = _id_column()
    tenant_id = sa.Column(sa.String(36), nullable=False)
    name = sa.Column(sa.String(15), nullable=False)

    plugin_labels = sa.Column(st.JsonDictType())
    version_labels = sa.Column(st.JsonDictType())
