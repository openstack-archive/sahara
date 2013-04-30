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

from mock import patch, Mock
from oslo.config import cfg
import unittest

from savanna.exceptions import NotFoundException, SavannaException
import savanna.openstack.common.exception as os_ex
from savanna.service.api import Resource
import savanna.service.validation as v


CONF = cfg.CONF
CONF.import_opt('allow_cluster_ops', 'savanna.config')


def _raise(ex):
    def function(*args, **kwargs):
        raise ex

    return function


def _cluster(base, **kwargs):
    base['cluster'].update(**kwargs)
    return base


def _template(base, **kwargs):
    base['node_template'].update(**kwargs)
    return base


class TestValidation(unittest.TestCase):
    def setUp(self):
        self._create_object_fun = None
        CONF.set_override('allow_cluster_ops', False)

    def tearDown(self):
        self._create_object_fun = None
        CONF.clear_override('allow_cluster_ops')

    @patch("savanna.utils.api.bad_request")
    @patch("savanna.utils.api.request_data")
    def test_malformed_request_body(self, request_data, bad_request):
        ex = os_ex.MalformedRequestBody()
        request_data.side_effect = _raise(ex)
        m_func = Mock()
        m_func.__name__ = "m_func"

        v.validate(m_func)(m_func)()

        self._assert_calls(bad_request,
                           (1, 'MALFORMED_REQUEST_BODY',
                            'Malformed message body: %(reason)s'))

    def _assert_exists_by_id(self, side_effect, assert_func=True):
        m_checker = Mock()
        m_checker.side_effect = side_effect
        m_func = Mock()
        m_func.__name__ = "m_func"

        v.exists_by_id(m_checker, "template_id")(m_func)(template_id="asd")

        m_checker.assert_called_once_with(id="asd")

        if assert_func:
            m_func.assert_called_once_with(template_id="asd")

    @patch("savanna.utils.api.internal_error")
    @patch("savanna.utils.api.not_found")
    def test_exists_by_id_passed(self, not_found, internal_error):
        self._assert_exists_by_id(None)

        self.assertEqual(not_found.call_count, 0)
        self.assertEqual(internal_error.call_count, 0)

    @patch("savanna.utils.api.internal_error")
    @patch("savanna.utils.api.not_found")
    def test_exists_by_id_failed(self, not_found, internal_error):
        self._assert_exists_by_id(_raise(NotFoundException("")), False)
        self.assertEqual(not_found.call_count, 1)
        self.assertEqual(internal_error.call_count, 0)

        self._assert_exists_by_id(_raise(SavannaException()), False)
        self.assertEqual(not_found.call_count, 1)
        self.assertEqual(internal_error.call_count, 1)

        self._assert_exists_by_id(_raise(AttributeError()), False)
        self.assertEqual(not_found.call_count, 1)
        self.assertEqual(internal_error.call_count, 2)

    def _assert_calls(self, mock, call_info):
        print "_assert_calls for %s, \n\t actual: %s , \n\t expected: %s" \
              % (mock, mock.call_args, call_info)
        if not call_info:
            self.assertEqual(mock.call_count, 0)
        else:
            self.assertEqual(mock.call_count, call_info[0])
            self.assertEqual(mock.call_args[0][0].code, call_info[1])
            self.assertEqual(mock.call_args[0][0].message, call_info[2])

    def _assert_create_object_validation(
            self, data, bad_req_i=None, not_found_i=None, int_err_i=None):

        request_data_p = patch("savanna.utils.api.request_data")
        bad_req_p = patch("savanna.utils.api.bad_request")
        not_found_p = patch("savanna.utils.api.not_found")
        int_err_p = patch("savanna.utils.api.internal_error")
        get_clusters_p = patch("savanna.service.api.get_clusters")
        get_templates_p = patch("savanna.service.api.get_node_templates")
        get_template_p = patch("savanna.service.api.get_node_template")
        get_types_p = patch("savanna.service.api.get_node_types")
        get_node_type_required_params_p = \
            patch("savanna.service.api.get_node_type_required_params")
        get_node_type_all_params_p = \
            patch("savanna.service.api.get_node_type_all_params")
        patchers = (request_data_p, bad_req_p, not_found_p, int_err_p,
                    get_clusters_p, get_templates_p, get_template_p,
                    get_types_p, get_node_type_required_params_p,
                    get_node_type_all_params_p)

        request_data = request_data_p.start()
        bad_req = bad_req_p.start()
        not_found = not_found_p.start()
        int_err = int_err_p.start()
        get_clusters = get_clusters_p.start()
        get_templates = get_templates_p.start()
        get_template = get_template_p.start()
        get_types = get_types_p.start()
        get_node_type_required_params = get_node_type_required_params_p.start()
        get_node_type_all_params = get_node_type_all_params_p.start()

        # stub clusters list
        get_clusters.return_value = getattr(self, "_clusters_data", [
            Resource("cluster", {
                "name": "some-cluster-1"
            })
        ])

        # stub node templates
        get_templates.return_value = getattr(self, "_templates_data", [
            Resource("node_template", {
                "name": "jt_nn.small",
                "node_type": {
                    "name": "JT+NN",
                    "processes": ["job_tracker", "name_node"]
                }
            }),
            Resource("node_template", {
                "name": "nn.small",
                "node_type": {
                    "name": "NN",
                    "processes": ["name_node"]
                }
            })
        ])

        def _get_template(name):
            for template in get_templates():
                if template.name == name:
                    return template
            return None

        get_template.side_effect = _get_template

        get_types.return_value = getattr(self, "_types_data", [
            Resource("node_type", {
                "name": "JT+NN",
                "processes": ["job_tracker", "name_node"]
            })
        ])

        def _get_r_params(name):
            if name == "JT+NN":
                return {"job_tracker": ["jt_param"]}
            return dict()

        get_node_type_required_params.side_effect = _get_r_params

        def _get_all_params(name):
            if name == "JT+NN":
                return {"job_tracker": ["jt_param"]}
            return dict()

        get_node_type_all_params.side_effect = _get_all_params

        # mock function that should be validated
        m_func = Mock()
        m_func.__name__ = "m_func"

        # request data to validate
        request_data.return_value = data

        v.validate(self._create_object_fun)(m_func)()

        self.assertEqual(request_data.call_count, 1)

        self._assert_calls(bad_req, bad_req_i)
        self._assert_calls(not_found, not_found_i)
        self._assert_calls(int_err, int_err_i)

        for patcher in patchers:
            patcher.stop()

    def test_cluster_create_v_required(self):
        self._create_object_fun = v.validate_cluster_create

        self._assert_create_object_validation(
            {},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'cluster' is a required property")
        )
        self._assert_create_object_validation(
            {"cluster": {}},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            {"cluster": {
                "name": "some-name"
            }},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'base_image_id' is a required property")
        )
        self._assert_create_object_validation(
            {"cluster": {
                "name": "some-name",
                "base_image_id": "some-image-id"
            }},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'node_templates' is a required property")
        )

    def test_cluster_create_v_name_base(self):
        self._create_object_fun = v.validate_cluster_create

        cluster = {
            "cluster": {
                "base_image_id": "some-image-id",
                "node_templates": {}
            }
        }
        self._assert_create_object_validation(
            _cluster(cluster, name=None),
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"None is not of type 'string'")
        )
        self._assert_create_object_validation(
            _cluster(cluster, name=""),
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'' is too short")
        )
        self._assert_create_object_validation(
            _cluster(cluster, name="a" * 51),
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'%s' is too long" % ('a' * 51))
        )

    def test_cluster_create_v_name_pattern(self):
        self._create_object_fun = v.validate_cluster_create

        cluster = {
            "cluster": {
                "base_image_id": "some-image-id",
                "node_templates": {}
            }
        }

        def _assert_cluster_name_pattern(self, name):
            cluster_schema = v.CLUSTER_CREATE_SCHEMA['properties']['cluster']
            name_p = cluster_schema['properties']['name']['pattern']
            self._assert_create_object_validation(
                _cluster(cluster, name=name),
                bad_req_i=(1, "VALIDATION_ERROR",
                           (u"'%s' does not match '%s'" % (name, name_p))
                           .replace('\\', "\\\\"))
            )

        _assert_cluster_name_pattern(self, "asd_123")
        _assert_cluster_name_pattern(self, "123")
        _assert_cluster_name_pattern(self, "asd?")

    def test_cluster_create_v_name_exists(self):
        self._create_object_fun = v.validate_cluster_create

        cluster = {
            "cluster": {
                "base_image_id": "some-image-id",
                "node_templates": {}
            }
        }

        self._assert_create_object_validation(
            _cluster(cluster, name="some-cluster-1"),
            bad_req_i=(1, "CLUSTER_NAME_ALREADY_EXISTS",
                       u"Cluster with name 'some-cluster-1' already exists")
        )

    def test_cluster_create_v_templates(self):
        self._create_object_fun = v.validate_cluster_create

        cluster = {
            "cluster": {
                "name": "some-cluster",
                "base_image_id": "some-image-id"
            }
        }
        self._assert_create_object_validation(
            _cluster(cluster, node_templates={}),
            bad_req_i=(1, "NOT_SINGLE_NAME_NODE",
                       u"Hadoop cluster should contain only 1 NameNode. "
                       u"Actual NN count is 0")
        )
        self._assert_create_object_validation(
            _cluster(cluster, node_templates={
                "nn.small": 1
            }),
            bad_req_i=(1, "NOT_SINGLE_JOB_TRACKER",
                       u"Hadoop cluster should contain only 1 JobTracker. "
                       u"Actual JT count is 0")
        )
        self._assert_create_object_validation(
            _cluster(cluster, node_templates={
                "incorrect_template": 10
            }),
            bad_req_i=(1, "NODE_TEMPLATE_NOT_FOUND",
                       u"NodeTemplate 'incorrect_template' not found")
        )
        self._assert_create_object_validation(
            _cluster(cluster, node_templates={
                "jt_nn.small": 1
            })
        )

    def test_node_template_create_v_required(self):
        self._create_object_fun = v.validate_node_template_create

        self._assert_create_object_validation(
            {},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'node_template' is a required property")
        )
        self._assert_create_object_validation(
            {"node_template": {}},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name' is a required property")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name"
            }},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'node_type' is a required property")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "some-node-type"
            }},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'flavor_id' is a required property")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1"
            }},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'name_node' is a required property")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {}
            }},
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'job_tracker' is a required property")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {}
            }},
            bad_req_i=(1, "REQUIRED_PARAM_MISSED",
                       u"Required parameter 'jt_param' of process "
                       u"'job_tracker' should be specified")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {"jt_param": ""}
            }},
            bad_req_i=(1, "REQUIRED_PARAM_MISSED",
                       u"Required parameter 'jt_param' of process "
                       u"'job_tracker' should be specified")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {"jt_param": "some value", "bad.parameter": "1"}
            }},
            bad_req_i=(1, "PARAM_IS_NOT_ALLOWED",
                       u"Parameter 'bad.parameter' "
                       u"of process 'job_tracker' is not allowed to change")
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {"jt_param": "some value"}
            }},
        )
        self._assert_create_object_validation(
            {"node_template": {
                "name": "some-name",
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {},
                "task_tracker": {}
            }},
            bad_req_i=(1, "NODE_PROCESS_DISCREPANCY",
                       u"Discrepancies in Node Processes. "
                       u"Required: ['name_node', 'job_tracker']")
        )

    def test_node_template_create_v_name_base(self):
        self._create_object_fun = v.validate_node_template_create

        template = {
            "node_template": {
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {}
            }
        }
        self._assert_create_object_validation(
            _template(template, name=None),
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"None is not of type 'string'")
        )
        self._assert_create_object_validation(
            _template(template, name=""),
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'' is too short")
        )
        self._assert_create_object_validation(
            _template(template, name="a" * 241),
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"'%s' is too long" % ('a' * 241))
        )

    def test_node_template_create_v_name_pattern(self):
        self._create_object_fun = v.validate_node_template_create

        template = {
            "node_template": {
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {}
            }
        }

        def _assert_template_name_pattern(self, name):
            schema_props = v.TEMPLATE_CREATE_SCHEMA['properties']
            template_schema = schema_props['node_template']
            name_p = template_schema['properties']['name']['pattern']
            self._assert_create_object_validation(
                _template(template, name=name),
                bad_req_i=(1, "VALIDATION_ERROR",
                           (u"'%s' does not match '%s'" % (name, name_p))
                           .replace('\\', "\\\\"))
            )

        _assert_template_name_pattern(self, "asd;123")
        _assert_template_name_pattern(self, "123")
        _assert_template_name_pattern(self, "asd?")

    def test_node_template_create_v_name_exists(self):
        self._create_object_fun = v.validate_node_template_create

        template = {
            "node_template": {
                "node_type": "JT+NN",
                "flavor_id": "flavor-1",
                "name_node": {},
                "job_tracker": {}
            }
        }

        self._assert_create_object_validation(
            _template(template, name="jt_nn.small"),
            bad_req_i=(1, "NODE_TEMPLATE_ALREADY_EXISTS",
                       u"NodeTemplate with name 'jt_nn.small' already exists")
        )

    def test_node_template_create_v_types(self):
        self._create_object_fun = v.validate_node_template_create

        self._assert_create_object_validation(
            {
                "node_template": {
                    "name": "some-name",
                    "node_type": "JJ",
                    "flavor_id": "flavor-1",
                    "name_node": {},
                    "job_tracker": {}
                }
            },
            bad_req_i=(1, "NODE_TYPE_NOT_FOUND",
                       u"NodeType 'JJ' not found")
        )

# TODO(slukjanov): add tests for allow_cluster_ops = True
