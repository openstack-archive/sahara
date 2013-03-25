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

import functools
import jsonschema
from flask import request
from savanna.service import api
from savanna.utils.api import request_data, bad_request, internal_error
from savanna.utils.openstack import nova
from savanna import exceptions as ex
from savanna.openstack.common.exception import MalformedRequestBody
from oslo.config import cfg
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_opt('allow_cluster_ops', 'savanna.config')

# Base validation schema of cluster creation operation
CLUSTER_CREATE_SCHEMA = {
    "title": "Cluster creation schema",
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 240,
                 "pattern": "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]"
                            "*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z]"
                            "[A-Za-z0-9\-]*[A-Za-z0-9])$"},
        "base_image_id": {"type": "string", "minLength": 1, "maxLength": 240},
        "node_templates": {
            "type": "object"
        }
    },
    "required": ["name", "base_image_id", "node_templates"]
}

# Base validation schema of node template creation operation
TEMPLATE_CREATE_SCHEMA = {
    "title": "Node Template creation schema",
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 240,
                 "pattern": "^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]"
                            "*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z]"
                            "[A-Za-z0-9\-]*[A-Za-z0-9])$"},
        "node_type": {"type": "string", "minLength": 1, "maxLength": 240},
        "flavor_id": {"type": "string", "minLength": 1, "maxLength": 240},
        "task_tracker": {
            "type": "object"
        },
        "job_tracker": {
            "type": "object"
        },
        "name_node": {
            "type": "object"
        },
        "data_node": {
            "type": "object"
        }
    },
    "required": ["name", "node_type", "flavor_id"]
}


def validate(validate_func):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            try:
                validate_func(request_data())
            except jsonschema.ValidationError, e:
                e.code = "VALIDATION_ERROR"
                return bad_request(e)
            except ex.SavannaException, e:
                return bad_request(e)
            except MalformedRequestBody, e:
                e.code = "MALFORMED_REQUEST_BODY"
                return bad_request(e)
            except Exception, e:
                internal_error(500, "Exception occurred during validation", e)

            return func(*args, **kwargs)

        return handler

    return decorator


def validate_cluster_create(cluster_values):
    values = cluster_values['cluster']
    jsonschema.validate(values, CLUSTER_CREATE_SCHEMA)

    # check that requested cluster name is unique
    unique_names = [cluster.name for cluster in api.get_clusters()]
    if values['name'] in unique_names:
        raise ex.ClusterNameExistedException(values['name'])

    # check that requested templates are from already defined values
    node_templates = values['node_templates']
    possible_node_templates = [nt.name for nt in api.get_node_templates()]
    for nt in node_templates:
        if nt not in possible_node_templates:
            raise ex.NodeTemplateNotFoundException(nt)
        # check node count is integer and non-zero value
        jsonschema.validate(node_templates[nt],
                            {"type": "integer", "minimum": 1})

    # check that requested cluster contains only 1 instance of NameNode
    # and 1 instance of JobTracker
    jt_count = 0
    nn_count = 0

    for nt_name in node_templates:
        processes = api.get_node_template(name=nt_name).dict['node_type'][
            'processes']
        if "job_tracker" in processes:
            jt_count += node_templates[nt_name]
        if "name_node" in processes:
            nn_count += node_templates[nt_name]

    if nn_count != 1:
        raise ex.NotSingleNameNodeException(nn_count)

    if jt_count != 1:
        raise ex.NotSingleJobTrackerException(jt_count)

    if CONF.allow_cluster_ops:
        image_id = values['base_image_id']
        nova_images = nova.get_images(request.headers)
        if image_id not in nova_images:
            LOG.debug("Could not find %s image in %s", image_id, nova_images)
            raise ex.ImageNotFoundException(values['base_image_id'])
    else:
        LOG.info("Cluster ops are disabled, use --allow-cluster-ops flag")


def validate_node_template_create(nt_values):
    values = nt_values['node_template']
    jsonschema.validate(values, TEMPLATE_CREATE_SCHEMA)

    # check that requested node_template name is unique
    unique_names = [nt.name for nt in api.get_node_templates()]
    if values['name'] in unique_names:
        raise ex.NodeTemplateExistedException(values['name'])

    node_types = [nt.name for nt in api.get_node_types()]

    if values['node_type'] not in node_types:
        raise ex.NodeTypeNotFoundException(values['node_type'])

    req_procs = []
    if "TT" in values['node_type']:
        req_procs.append("task_tracker")
    if "DN" in values['node_type']:
        req_procs.append("data_node")
    if "NN" in values['node_type']:
        req_procs.append("name_node")
    if "JT" in values['node_type']:
        req_procs.append("job_tracker")

    LOG.debug("Required properties are: %s", req_procs)

    jsonschema.validate(values, {"required": req_procs})

    processes = values.copy()
    del processes['name']
    del processes['node_type']
    del processes['flavor_id']

    LOG.debug("Incoming properties are: %s", processes)

    for proc in processes:
        if proc not in req_procs:
            raise ex.DiscrepancyNodeProcessException(req_procs)

    if api.CONF.allow_cluster_ops:
        flavor = values['flavor_id']
        nova_flavors = nova.get_flavors(request.headers)
        if flavor not in nova_flavors:
            LOG.debug("Could not find %s flavor in %s", flavor, nova_flavors)
            raise ex.FlavorNotFoundException(flavor)
    else:
        LOG.info("Cluster ops are disabled, use --allow-cluster-ops flag")
