# Copyright (c) 2016 Red Hat, Inc.
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

import six

from sahara.api import acl
from sahara.service import api
from sahara.service import validation as v
from sahara.service.validations import clusters as v_c
from sahara.service.validations import clusters_scaling as v_c_s
from sahara.service.validations import clusters_schema as v_c_schema
import sahara.utils.api as u


rest = u.RestV2('clusters', __name__)


@rest.get('/clusters')
@acl.enforce("data-processing:clusters:get_all")
def clusters_list():
    return u.render(clusters=[c.to_dict() for c in api.get_clusters(
        **u.get_request_args().to_dict())])


@rest.post('/clusters')
@acl.enforce("data-processing:clusters:create")
@v.validate(v_c_schema.CLUSTER_SCHEMA, v_c.check_cluster_create)
def clusters_create(data):
    return u.render(api.create_cluster(data).to_wrapped_dict())


@rest.post('/clusters/multiple')
@acl.enforce("data-processing:clusters:create")
@v.validate(
    v_c_schema.MULTIPLE_CLUSTER_SCHEMA, v_c.check_multiple_clusters_create)
def clusters_create_multiple(data):
    return u.render(api.create_multiple_clusters(data))


@rest.put('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:scale")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_SCALING_SCHEMA, v_c_s.check_cluster_scaling)
def clusters_scale(cluster_id, data):
    return u.to_wrapped_dict(api.scale_cluster, cluster_id, data)


@rest.get('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:get")
@v.check_exists(api.get_cluster, 'cluster_id')
def clusters_get(cluster_id):
    data = u.get_request_args()
    show_events = six.text_type(
        data.get('show_progress', 'false')).lower() == 'true'
    return u.to_wrapped_dict(api.get_cluster, cluster_id, show_events)


@rest.patch('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:modify")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(v_c_schema.CLUSTER_UPDATE_SCHEMA, v_c.check_cluster_update)
def clusters_update(cluster_id, data):
    return u.to_wrapped_dict(api.update_cluster, cluster_id, data)


@rest.delete('/clusters/<cluster_id>')
@acl.enforce("data-processing:clusters:delete")
@v.check_exists(api.get_cluster, 'cluster_id')
@v.validate(None, v_c.check_cluster_delete)
def clusters_delete(cluster_id):
    api.terminate_cluster(cluster_id)
    return u.render()
