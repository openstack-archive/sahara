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

from savanna.service import api

from savanna.utils.api import Rest, render, abort_and_log, request_data
from savanna.service.validation import validate, validate_cluster_create, \
    validate_node_template_create
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)

rest = Rest('v02', __name__)


@rest.get('/node-templates')
def templates_list():
    try:
        return render(
            node_templates=[nt.dict for nt in api.get_node_templates()])
    except Exception, e:
        abort_and_log(500, "Exception while listing NodeTemplates", e)


@rest.post('/node-templates')
@validate(validate_node_template_create)
def templates_create():
    return render(api.create_node_template(request_data()).wrapped_dict)


@rest.get('/node-templates/<template_id>')
def templates_get(template_id):
    nt = None
    try:
        nt = api.get_node_template(id=template_id)
    except Exception, e:
        abort_and_log(500, "Exception while getting NodeTemplate by id "
                           "'%s'" % template_id, e)
    if nt is None:
        abort_and_log(404, "NodeTemplate with id '%s' not found"
                           % template_id)

    return render(nt.wrapped_dict)


@rest.put('/node-templates/<template_id>')
def templates_update(template_id):
    raise NotImplementedError("Template update op isn't implemented (id '%s')"
                              % template_id)


@rest.delete('/node-templates/<template_id>')
def templates_delete(template_id):
    api.terminate_node_template(id=template_id)
    return render()


@rest.get('/clusters')
def clusters_list():
    try:
        return render(clusters=[c.dict for c in api.get_clusters()])
    except Exception, e:
        abort_and_log(500, 'Exception while listing Clusters', e)


@rest.post('/clusters')
@validate(validate_cluster_create)
def clusters_create():
    return render(api.create_cluster(request_data()).wrapped_dict)


@rest.get('/clusters/<cluster_id>')
def clusters_get(cluster_id):
    c = None
    try:
        c = api.get_cluster(id=cluster_id)
    except Exception, e:
        abort_and_log(500, 'Exception while getting Cluster with id '
                           '\'%s\'' % cluster_id, e)

    if c is None:
        abort_and_log(404, 'Cluster with id \'%s\' not found' % cluster_id)

    return render(c.wrapped_dict)


@rest.put('/clusters/<cluster_id>')
def clusters_update(cluster_id):
    raise NotImplementedError("Cluster update op isn't implemented (id '%s')"
                              % cluster_id)


@rest.delete('/clusters/<cluster_id>')
def clusters_delete(cluster_id):
    api.terminate_cluster(id=cluster_id)
    return render()
