from uuid import uuid4

from eho.server.storage.storage import db


class BaseModel(object):
    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)


class NodeTemplate(db.Model, BaseModel):
    __tablename__ = 'NodeTemplate'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    node_type_id = db.Column(db.String(36), db.ForeignKey('NodeType.id'),
                             nullable=False)
    tenant_id = db.Column(db.String(36), nullable=False)  # is it needed?
    flavor_id = db.Column(db.String(36), nullable=False)

    node_template_configs = db.relationship('NodeTemplateConfig',
                                            cascade="all,delete",
                                            backref='node_template')
    cluster_node_counts = db.relationship('ClusterNodeCount',
                                          cascade="all,delete",
                                          backref='node_template')
    nodes = db.relationship('Node', cascade="all,delete",
                            backref='node_template')

    def __init__(self, name, node_type_id, tenant_id, flavor_id):
        self.id = uuid4().hex
        self.name = name
        self.node_type_id = node_type_id
        self.tenant_id = tenant_id
        self.flavor_id = flavor_id

    def __repr__(self):
        return '<NodeTemplate %s / %s>' % (self.name, self.node_type_id)


class Cluster(db.Model, BaseModel):
    __tablename__ = 'Cluster'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    base_image_id = db.Column(db.String(36), nullable=False)
    status = db.Column(db.String(80))
    tenant_id = db.Column(db.String(36), nullable=False)

    nodes = db.relationship('Node', cascade="all,delete", backref='cluster')
    service_urls = db.relationship('ServiceUrl', cascade="all,delete",
                                   backref='cluster')
    node_counts = db.relationship('ClusterNodeCount', cascade="all,delete",
                                  backref='cluster')

    # node_templates: [(node_template_id, count), ...]

    def __init__(self, name, base_image_id, tenant_id, status=None):
        self.id = uuid4().hex
        self.name = name
        self.base_image_id = base_image_id
        if not status:
            status = 'Starting'
        self.status = status
        self.tenant_id = tenant_id

    def __repr__(self):
        return '<Cluster %s / %s>' % (self.name, self.status)


node_type_node_process = db.Table('NodeType_NodeProcess', db.metadata,
                                  db.Column('node_type_id', db.String(36),
                                            db.ForeignKey('NodeType.id')),
                                  db.Column('node_process_id', db.String(36),
                                            db.ForeignKey('NodeProcess.id')))


class NodeType(db.Model, BaseModel):
    __tablename__ = 'NodeType'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    processes = db.relationship('NodeProcess',
                                cascade="all,delete",
                                secondary=node_type_node_process,
                                backref='node_types')
    node_templates = db.relationship('NodeTemplate', cascade="all,delete",
                                     backref='node_type')

    def __init__(self, name):
        self.id = uuid4().hex
        self.name = name

    def __repr__(self):
        return '<NodeType %s>' % self.name


class NodeProcess(db.Model, BaseModel):
    __tablename__ = 'NodeProcess'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    node_process_properties = db.relationship('NodeProcessProperty',
                                              cascade="all,delete",
                                              backref='node_process')

    def __init__(self, name):
        self.id = uuid4().hex
        self.name = name

    def __repr__(self):
        return '<NodeProcess %s>' % self.name


class NodeProcessProperty(db.Model, BaseModel):
    __tablename__ = 'NodeProcessProperty'
    __table_args__ = (
        db.UniqueConstraint('node_process_id', 'name'),
    )

    id = db.Column(db.String(36), primary_key=True)
    node_process_id = db.Column(db.String(36), db.ForeignKey('NodeProcess.id'))
    name = db.Column(db.String(80), nullable=False)
    required = db.Column(db.Boolean, nullable=False)
    default = db.Column(db.String(36))
    node_template_configs = db.relationship('NodeTemplateConfig',
                                            cascade="all,delete",
                                            backref='node_process_property')

    def __init__(self, node_process_id, name, required=True, default=None):
        self.id = uuid4().hex
        self.node_process_id = node_process_id
        self.name = name
        self.required = required
        self.default = default

    def __repr__(self):
        return '<NodeProcessProperty %s>' % self.name


class NodeTemplateConfig(db.Model, BaseModel):
    __tablename__ = 'NodeTemplateConfig'
    __table_args__ = (
        db.UniqueConstraint('node_template_id', 'node_process_property_id'),
    )

    id = db.Column(db.String(36), primary_key=True)
    node_template_id = db.Column(
        db.String(36),
        db.ForeignKey('NodeTemplate.id'))
    node_process_property_id = db.Column(
        db.String(36),
        db.ForeignKey('NodeProcessProperty.id'))
    value = db.Column(db.String(36))

    def __init__(self, node_template_id, node_process_property_id, value):
        self.id = uuid4().hex
        self.node_template_id = node_template_id
        self.node_process_property_id = node_process_property_id
        self.value = value

    def __repr__(self):
        return '<NodeTemplateConfig %s.%s / %s>' \
               % (self.node_template_id, self.node_process_property_id,
                  self.value)


class ClusterNodeCount(db.Model, BaseModel):
    __tablename__ = 'ClusterNodeCount'
    __table_args__ = (
        db.UniqueConstraint('cluster_id', 'node_template_id'),
    )

    id = db.Column(db.String(36), primary_key=True)
    cluster_id = db.Column(db.String(36), db.ForeignKey('Cluster.id'))
    node_template_id = db.Column(db.String(36),
                                 db.ForeignKey('NodeTemplate.id'))
    count = db.Column(db.Integer, nullable=False)

    def __init__(self, cluster_id, node_template_id, count):
        self.id = uuid4().hex
        self.cluster_id = cluster_id
        self.node_template_id = node_template_id
        self.count = count

    def __repr__(self):
        return '<ClusterNodeCount %s / %s>' \
               % (self.node_template_id, self.count)


class Node(db.Model, BaseModel):
    __tablename__ = 'Node'

    # do we need own id?
    vm_id = db.Column(db.String(36), primary_key=True)
    cluster_id = db.Column(db.String(36), db.ForeignKey('Cluster.id'))
    node_template_id = db.Column(db.String(36),
                                 db.ForeignKey('NodeTemplate.id'))

    def __init__(self, vm_id, cluster_id, node_template_id):
        self.vm_id = vm_id
        self.cluster_id = cluster_id
        self.node_template_id = node_template_id

    def __repr__(self):
        return '<Node based on %s>' % self.node_template.name


class ServiceUrl(db.Model, BaseModel):
    __tablename__ = 'ServiceUrl'

    id = db.Column(db.String(36), primary_key=True)
    cluster_id = db.Column(db.String(36), db.ForeignKey('Cluster.id'))
    name = db.Column(db.String(80))
    url = db.Column(db.String(80), nullable=False)

    def __init__(self, cluster_id, name, url):
        self.id = uuid4().hex
        self.cluster_id = cluster_id
        self.name = name
        self.url = url

    def __repr__(self):
        return '<ServiceUrl %s / %s>' % (self.name, self.url)
