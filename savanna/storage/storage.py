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

from savanna.storage.db import DB

from savanna.storage.models import NodeTemplate, NodeProcess, Cluster, \
    ClusterNodeCount, NodeTemplateConfig, NodeType, NodeProcessProperty


## Node Template ops:

def get_node_template(**args):
    return NodeTemplate.query.filter_by(**args).first()


def get_node_templates(**args):
    return NodeTemplate.query.filter_by(**args).all()


def is_node_template_associated(**args):
    nt = get_node_template(**args)
    return nt and (len(nt.nodes) or len(nt.cluster_node_counts))


def create_node_template(name, node_type_id, flavor_id, configs):
    """Creates new node templates.

    :param name: template name
    :param node_type_id: node type
    :param flavor_id: flavor
    :param configs: dict of process->property->value
    :return: created node template
    """
    node_template = NodeTemplate(name, node_type_id, flavor_id)
    DB.session.add(node_template)
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
            DB.session.add(NodeTemplateConfig(node_template.id, prop.id, val))
    DB.session.commit()

    return node_template


def terminate_node_template(**args):
    template = get_node_template(**args)
    if template:
        DB.session.delete(template)
        DB.session.commit()
        return True
    else:
        return False


## Cluster ops:

def get_cluster(**args):
    return Cluster.query.filter_by(**args).first()


def get_clusters(**args):
    return Cluster.query.filter_by(**args).all()


def create_cluster(name, base_image_id, tenant_id, templates):
    """Creates new cluster.

    :param name: cluster name
    :param base_image_id: base image
    :param tenant_id: tenant
    :param templates: dict of template->count
    :return: created cluster
    """
    cluster = Cluster(name, base_image_id, tenant_id)
    DB.session.add(cluster)
    for template in templates:
        count = templates.get(template)
        template_id = get_node_template(name=template).id
        cnc = ClusterNodeCount(cluster.id, template_id, int(count))
        DB.session.add(cnc)
    DB.session.commit()

    return cluster


def terminate_cluster(**args):
    cluster = get_cluster(**args)
    DB.session.delete(cluster)
    DB.session.commit()


def update_cluster_status(new_status, **args):
    cluster = Cluster.query.filter_by(**args).first()
    cluster.status = new_status
    DB.session.add(cluster)
    DB.session.commit()

    return cluster


## Node Process ops:

def create_node_process(name, properties):
    """Creates new node process and node process properties.

    :param name: process name
    :param properties: array of triples (name, required, default)
    :return: created node process
    """
    process = NodeProcess(name)
    DB.session.add(process)
    DB.session.commit()
    for p in properties:
        prop = NodeProcessProperty(process.id, p[0], p[1], p[2])
        DB.session.add(prop)
    DB.session.commit()

    return process


## Node Type ops:

def get_node_type(**args):
    return NodeType.query.filter_by(**args).first()


def get_node_types(**args):
    return NodeType.query.filter_by(**args).all()


def create_node_type(name, processes):
    """Creates new node type using specified list of processes

    :param name:
    :param processes:
    :return:
    """
    node_type = NodeType(name)
    node_type.processes = processes
    DB.session.add(node_type)
    DB.session.commit()

    return node_type
