import logging

import eventlet

from eho.server.storage.models import NodeTemplate, NodeType, NodeProcess, \
    NodeTemplateConfig, Cluster, ClusterNodeCount
from eho.server.storage.storage import DB
from eho.server.utils.api import abort_and_log
from eho.server.service import cluster_ops
from flask import request


ALLOW_CLUSTER_OPS = False


def setup_api(app):
    global ALLOW_CLUSTER_OPS
    ALLOW_CLUSTER_OPS = app.config['ALLOW_CLUSTER_OPS']


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
    return [_node_template(tmpl) for tmpl
            in NodeTemplate.query.filter_by(**args).all()]


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

    nt = NodeTemplate(name, node_type_id, tenant_id, flavor_id)
    DB.session.add(nt)
    for process_name in values:
        process = NodeProcess.query.filter_by(name=process_name).first()
        conf = values.get(process_name)
        for prop in process.node_process_properties:
            val = conf.get(prop.name, None)
            if not val and prop.required:
                if not prop.default:
                    raise RuntimeError('Template \'%s\', value missed '
                                       'for required param: %s %s'
                                       % (name, process.name, prop.name))
                val = prop.default
            DB.session.add(NodeTemplateConfig(nt.id, prop.id, val))
    DB.session.commit()

    return get_node_template(id=nt.id)


def _cluster(cluster):
    if not cluster:
        abort_and_log(404, 'Cluster not found')
    d = {
        'id': cluster.id,
        'name': cluster.name,
        'base_image_id': cluster.base_image_id,
        'status': cluster.status,
        'tenant_id': cluster.tenant_id,
        'service_urls': {},
        'node_templates': {},
        'nodes': [{'vm_id': n.vm_id,
                   'node_template': {
                       'id': n.node_template.id,
                       'name': n.node_template.name
                   }}
                  for n in cluster.nodes]
    }
    for ntc in cluster.node_counts:
        d['node_templates'][ntc.node_template.name] = ntc.count

    for service in cluster.service_urls:
        d['service_urls'][service.name] = service.url

    return Resource('Cluster', d)


def get_cluster(**args):
    return _cluster(Cluster.query.filter_by(**args).first())


def get_clusters(**args):
    return [_cluster(cluster) for cluster in
            Cluster.query.filter_by(**args).all()]


def create_cluster(values):
    name = values.pop('name')
    base_image_id = values.pop('base_image_id')
    tenant_id = values.pop('tenant_id')
    templates = values.pop('node_templates')

    cluster = Cluster(name, base_image_id, tenant_id)
    DB.session.add(cluster)
    for template in templates:
        count = templates.get(template)
        template_id = _template_id_by_name(template)
        cnc = ClusterNodeCount(cluster.id, template_id, int(count))
        DB.session.add(cnc)
    DB.session.commit()

    eventlet.spawn(_cluster_creation_job, request.headers, cluster.id)

    return get_cluster(id=cluster.id)


def _cluster_creation_job(headers, cluster_id):
    cluster = Cluster.query.filter_by(id=cluster_id).first()
    logging.debug("Starting cluster '%s' creation: %s", cluster_id,
                  _cluster(cluster).dict)

    if ALLOW_CLUSTER_OPS:
        cluster_ops.launch_cluster(headers, cluster)
    else:
        logging.info("Cluster ops are disabled, use --allow-cluster-ops flag")

    # update cluster status
    cluster = Cluster.query.filter_by(id=cluster.id).first()
    cluster.status = 'Active'
    DB.session.add(cluster)
    DB.session.commit()


def terminate_cluster(**args):
    # update cluster status
    cluster = Cluster.query.filter_by(**args).first()
    cluster.status = 'Stoping'
    DB.session.add(cluster)
    DB.session.commit()

    eventlet.spawn(_cluster_termination_job, request.headers, cluster.id)


def _cluster_termination_job(headers, cluster_id):
    cluster = Cluster.query.filter_by(id=cluster_id).first()
    logging.debug("Stoping cluster '%s' creation: %s", cluster_id,
                  _cluster(cluster).dict)

    if ALLOW_CLUSTER_OPS:
        cluster_ops.stop_cluster(headers, cluster)
    else:
        logging.info("Cluster ops are disabled, use --allow-cluster-ops flag")

    DB.session.delete(cluster)
    DB.session.commit()


def terminate_node_template(**args):
    template = NodeTemplate.query.filter_by(**args).first()
    if template:
        if len(template.nodes):
            abort_and_log(500, "There are active nodes created using "
                               "template '%s' you trying to terminate"
                               % args)
        else:
            DB.session.delete(template)
            DB.session.commit()

        return True
    else:
        return False
