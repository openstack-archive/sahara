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

from savanna.storage.db import DB


class NodeTemplate(DB.Model):
    __tablename__ = 'NodeTemplate'

    id = DB.Column(DB.String(36), primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    node_type_id = DB.Column(DB.String(36), DB.ForeignKey('NodeType.id'),
                             nullable=False)
    flavor_id = DB.Column(DB.String(36), nullable=False)

    node_template_configs = DB.relationship('NodeTemplateConfig',
                                            cascade="all,delete",
                                            backref='node_template')
    cluster_node_counts = DB.relationship('ClusterNodeCount',
                                          cascade="all,delete",
                                          backref='node_template')
    nodes = DB.relationship('Node', cascade="all,delete",
                            backref='node_template')

    def __init__(self, name, node_type_id, flavor_id):
        self.id = uuid.uuid4().hex
        self.name = name
        self.node_type_id = node_type_id
        self.flavor_id = flavor_id

    def __repr__(self):
        return '<NodeTemplate %s / %s>' % (self.name, self.node_type_id)


class Cluster(DB.Model):
    __tablename__ = 'Cluster'

    id = DB.Column(DB.String(36), primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    base_image_id = DB.Column(DB.String(36), nullable=False)
    status = DB.Column(DB.String(80))
    tenant_id = DB.Column(DB.String(36), nullable=False)

    nodes = DB.relationship('Node', cascade="all,delete", backref='cluster')
    service_urls = DB.relationship('ServiceUrl', cascade="all,delete",
                                   backref='cluster')
    node_counts = DB.relationship('ClusterNodeCount', cascade="all,delete",
                                  backref='cluster')

    # node_templates: [(node_template_id, count), ...]

    def __init__(self, name, base_image_id, tenant_id, status=None):
        self.id = uuid.uuid4().hex
        self.name = name
        self.base_image_id = base_image_id
        if not status:
            status = 'Starting'
        self.status = status
        self.tenant_id = tenant_id

    def __repr__(self):
        return '<Cluster %s / %s>' % (self.name, self.status)


NODE_TYPE_NODE_PROCESS = DB.Table('NodeType_NodeProcess', DB.metadata,
                                  DB.Column('node_type_id', DB.String(36),
                                            DB.ForeignKey('NodeType.id')),
                                  DB.Column('node_process_id', DB.String(36),
                                            DB.ForeignKey('NodeProcess.id')))


class NodeType(DB.Model):
    __tablename__ = 'NodeType'

    id = DB.Column(DB.String(36), primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    processes = DB.relationship('NodeProcess',
                                cascade="all,delete",
                                secondary=NODE_TYPE_NODE_PROCESS,
                                backref='node_types')
    node_templates = DB.relationship('NodeTemplate', cascade="all,delete",
                                     backref='node_type')

    def __init__(self, name):
        self.id = uuid.uuid4().hex
        self.name = name

    def __repr__(self):
        return '<NodeType %s>' % self.name


class NodeProcess(DB.Model):
    __tablename__ = 'NodeProcess'

    id = DB.Column(DB.String(36), primary_key=True)
    name = DB.Column(DB.String(80), unique=True, nullable=False)
    node_process_properties = DB.relationship('NodeProcessProperty',
                                              cascade="all,delete",
                                              backref='node_process')

    def __init__(self, name):
        self.id = uuid.uuid4().hex
        self.name = name

    def __repr__(self):
        return '<NodeProcess %s>' % self.name


class NodeProcessProperty(DB.Model):
    __tablename__ = 'NodeProcessProperty'
    __table_args__ = (
        DB.UniqueConstraint('node_process_id', 'name'),
    )

    id = DB.Column(DB.String(36), primary_key=True)
    node_process_id = DB.Column(DB.String(36), DB.ForeignKey('NodeProcess.id'))
    name = DB.Column(DB.String(80), nullable=False)
    required = DB.Column(DB.Boolean, nullable=False)
    default = DB.Column(DB.String(36))
    node_template_configs = DB.relationship('NodeTemplateConfig',
                                            cascade="all,delete",
                                            backref='node_process_property')

    def __init__(self, node_process_id, name, required=True, default=None):
        self.id = uuid.uuid4().hex
        self.node_process_id = node_process_id
        self.name = name
        self.required = required
        self.default = default

    def __repr__(self):
        return '<NodeProcessProperty %s>' % self.name


class NodeTemplateConfig(DB.Model):
    __tablename__ = 'NodeTemplateConfig'
    __table_args__ = (
        DB.UniqueConstraint('node_template_id', 'node_process_property_id'),
    )

    id = DB.Column(DB.String(36), primary_key=True)
    node_template_id = DB.Column(
        DB.String(36),
        DB.ForeignKey('NodeTemplate.id'))
    node_process_property_id = DB.Column(
        DB.String(36),
        DB.ForeignKey('NodeProcessProperty.id'))
    value = DB.Column(DB.String(36))

    def __init__(self, node_template_id, node_process_property_id, value):
        self.id = uuid.uuid4().hex
        self.node_template_id = node_template_id
        self.node_process_property_id = node_process_property_id
        self.value = value

    def __repr__(self):
        return '<NodeTemplateConfig %s.%s / %s>' \
               % (self.node_template_id, self.node_process_property_id,
                  self.value)


class ClusterNodeCount(DB.Model):
    __tablename__ = 'ClusterNodeCount'
    __table_args__ = (
        DB.UniqueConstraint('cluster_id', 'node_template_id'),
    )

    id = DB.Column(DB.String(36), primary_key=True)
    cluster_id = DB.Column(DB.String(36), DB.ForeignKey('Cluster.id'))
    node_template_id = DB.Column(DB.String(36),
                                 DB.ForeignKey('NodeTemplate.id'))
    count = DB.Column(DB.Integer, nullable=False)

    def __init__(self, cluster_id, node_template_id, count):
        self.id = uuid.uuid4().hex
        self.cluster_id = cluster_id
        self.node_template_id = node_template_id
        self.count = count

    def __repr__(self):
        return '<ClusterNodeCount %s / %s>' \
               % (self.node_template_id, self.count)


class Node(DB.Model):
    __tablename__ = 'Node'

    # do we need own id?
    vm_id = DB.Column(DB.String(36), primary_key=True)
    cluster_id = DB.Column(DB.String(36), DB.ForeignKey('Cluster.id'))
    node_template_id = DB.Column(DB.String(36),
                                 DB.ForeignKey('NodeTemplate.id'))

    def __init__(self, vm_id, cluster_id, node_template_id):
        self.vm_id = vm_id
        self.cluster_id = cluster_id
        self.node_template_id = node_template_id

    def __repr__(self):
        return '<Node based on %s>' % self.node_template.name


class ServiceUrl(DB.Model):
    __tablename__ = 'ServiceUrl'

    id = DB.Column(DB.String(36), primary_key=True)
    cluster_id = DB.Column(DB.String(36), DB.ForeignKey('Cluster.id'))
    name = DB.Column(DB.String(80))
    url = DB.Column(DB.String(80), nullable=False)

    def __init__(self, cluster_id, name, url):
        self.id = uuid.uuid4().hex
        self.cluster_id = cluster_id
        self.name = name
        self.url = url

    def __repr__(self):
        return '<ServiceUrl %s / %s>' % (self.name, self.url)
