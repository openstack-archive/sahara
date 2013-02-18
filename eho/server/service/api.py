from eho.server.storage.models import *
from eho.server.storage.storage import db
from eho.server.utils.api import abort_and_log


def _clean_nones(obj):
    d_type = type(obj)
    if d_type is not dict or d_type is not list:
        return obj

    if d_type is dict:
        remove = []
        for key in obj:
            value = _clean_nones(obj.get(key))
            if value is None or len(value) == 0:
                remove.append(key)
        for key in remove:
            obj.pop(key)
    elif d_type is list:
        new_list = []
        for elem in obj:
            elem = _clean_nones(elem)
            if elem is not None and len(elem) == 0:
                new_list.append(elem)
        return new_list

    return obj


class Resource(object):
    def __init__(self, _name, _info):
        self._name = _name
        self._info = _clean_nones(_info)

    def __getattr__(self, k):
        if k not in self.__dict__:
            return self._info.get(k)
        return self.__dict__[k]

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self._info == other._info

    def __repr__(self):
        return '<%s %s>' % (self._name, self._info)

    @property
    def dict(self):
        return self._info


def _node_template(nt):
    if not nt:
        abort_and_log(404, 'NodeTemplate not found')
    d = {
        'id': nt.id,
        'name': nt.name,
        'node_type': {
            'id': nt.node_type.id,
            'name': nt.node_type.name,
            'processes': [p.name for p in nt.node_type.processes]},
        'tenant_id': nt.tenant_id,
        'flavor_id': nt.flavor_id
    }
    for conf in nt.node_template_configs:
        c_section = conf.node_process_property.node_process.name
        c_name = conf.node_process_property.name
        c_value = conf.value
        if c_section not in d:
            d[c_section] = dict()
        d[c_section][c_name] = c_value

    return Resource('NodeTemplate', d)


def _template_id_by_name(template):
    return NodeTemplate.query.filter_by(name=template).first().id


def _type_id_by_name(_type):
    return NodeType.query.filter_by(name=_type).first().id


def get_node_template(**args):
    return _node_template(NodeTemplate.query.filter_by(**args).first())


def get_node_templates(**args):
    return map(_node_template, NodeTemplate.query.filter_by(**args).all())


def create_node_template(values):
    """
    Creates new node template from values dict
    :param values: dict
    :return: created node template resource
    """
    name = values.pop('name')
    node_type_id = _type_id_by_name(values.pop('node_type'))
    tenant_id = values.pop('tenant_id')
    flavor_id = values.pop('flavor_id')
    configs = values.pop('configs', None)

    nt = NodeTemplate(name, node_type_id, tenant_id, flavor_id)
    db.session.add(nt)
    if configs:
        for process_name in configs:
            process = NodeProcess.query.filter_by(name=process_name).first()
            conf = configs.get(process_name)
            for prop in process.node_process_properties:
                val = conf.get(prop.name, None)
                if not val and prop.required:
                    if not prop.default:
                        raise RuntimeError('Template \'%s\', value missed '
                                           'for required param: %s %s'
                                           % (name, process.name, prop.name))
                    val = prop.default
                db.session.add(NodeTemplateConfig(nt.id, prop.id, val))
    db.session.commit()

    return get_node_template(id=nt.id)


def _cluster(c):
    if not c:
        abort_and_log(404, 'Cluster not found')
    d = {
        'id': c.id,
        'name': c.name,
        'base_image_id': c.base_image_id,
        'status': c.status,
        'tenant_id': c.tenant_id,
        'service_urls': {},
        'node_templates': {},
        'nodes': [{'vm_id': n.vm_id,
                   'node_template': {'id': n.node_template.id}}
                  for n in c.nodes]
    }
    for ntc in c.node_counts:
        d['node_templates'][ntc.node_template.name] = ntc.count

    return Resource('Cluster', d)


def get_cluster(**args):
    return _cluster(Cluster.query.filter_by(**args).first())


def get_clusters(**args):
    return map(_cluster, Cluster.query.filter_by(**args).all())


def create_cluster(values):
    name = values.pop('name')
    base_image_id = values.pop('base_image_id')
    tenant_id = values.pop('tenant_id')
    templates = values.pop('templates')

    cluster = Cluster(name, base_image_id, tenant_id)
    db.session.add(cluster)
    for template in templates:
        count = templates.get(template)
        template_id = _template_id_by_name(template)
        cnc = ClusterNodeCount(cluster.id, template_id, int(count))
        db.session.add(cnc)
    db.session.commit()

    return get_cluster(id=cluster.id)
