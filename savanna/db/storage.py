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

from savanna import context as ctx
import savanna.db.models as m


## Cluster ops
# TODO(slukjanov): check tenant_id and etc.

def get_clusters(**args):
    return ctx.model_query(m.Cluster).filter_by(**args).all()


def get_cluster(**args):
    return ctx.model_query(m.Cluster).filter_by(**args).first()


def create_cluster(values):
    session = ctx.current().session
    with session.begin():
        values['tenant_id'] = ctx.current().tenant_id
        ngs_vals = values.pop('node_groups', [])
        cluster_tmpl_id = values.pop('cluster_template_id', None)
        if cluster_tmpl_id:
            cluster_tmpl = get_cluster_template(id=cluster_tmpl_id)
            cluster = cluster_tmpl.to_cluster(values)
        else:
            cluster = m.Cluster(**values)

        if not ngs_vals and cluster_tmpl_id:
            # copy node groups from cluster template
            ngs_vals = cluster_tmpl.dict['node_groups']

        for ng in ngs_vals:
            tmpl_id = ng.get('node_group_template_id')
            if tmpl_id:
                tmpl = get_node_group_template(id=tmpl_id)
                node_group = tmpl.to_object(ng, m.NodeGroup)
            else:
                node_group = m.NodeGroup(**ng)
            cluster.node_groups.append(node_group)
            session.add(node_group)
        session.add(cluster)

        return cluster


def terminate_cluster(cluster):
    with ctx.current().session.begin():
        ctx.current().session.delete(cluster)


## ClusterTemplate ops

def get_cluster_templates(**args):
    return ctx.model_query(m.ClusterTemplate).filter_by(**args).all()


def get_cluster_template(**args):
    return ctx.model_query(m.ClusterTemplate).filter_by(**args).first()


def create_cluster_template(values):
    session = ctx.current().session
    with session.begin():
        values['tenant_id'] = ctx.current().tenant_id
        ngts_vals = values.pop('node_groups', [])
        cluster_template = m.ClusterTemplate(**values)
        for ngt in ngts_vals:
            tmpl_id = ngt.get('node_group_template_id')
            if tmpl_id:
                tmpl = get_node_group_template(id=tmpl_id)
                node_group = tmpl.to_object(
                    ngt, m.TemplatesRelation,
                    dict(cluster_template_id=cluster_template.id))
            else:
                node_group = m.TemplatesRelation(
                    cluster_template_id=cluster_template.id, **ngt)
            cluster_template.templates_relations.append(node_group)
            session.add(node_group)
        session.add(cluster_template)

        return cluster_template


def persist_cluster_template(cluster_template):
    session = ctx.current().session
    with session.begin():
        session.add(cluster_template)

    return cluster_template


def terminate_cluster_template(**args):
    with ctx.current().session.begin():
        ctx.current().session.delete(get_cluster_template(**args))


## NodeGroupTemplate ops

def get_node_group_templates(**args):
    return ctx.model_query(m.NodeGroupTemplate).filter_by(**args).all()


def get_node_group_template(**args):
    return ctx.model_query(m.NodeGroupTemplate).filter_by(**args).first()


def create_node_group_template(values):
    session = ctx.current().session
    with session.begin():
        values['tenant_id'] = ctx.current().tenant_id
        node_group_template = m.NodeGroupTemplate(**values)
        session.add(node_group_template)
        return node_group_template


def terminate_node_group_template(**args):
    with ctx.current().session.begin():
        ctx.current().session.delete(get_node_group_template(**args))
