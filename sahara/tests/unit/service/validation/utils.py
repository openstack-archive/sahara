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

import ast
import re
from unittest import mock

from neutronclient.common import exceptions as neutron_ex
import novaclient.exceptions as nova_ex
import six

from sahara.conductor import resource as r
from sahara.plugins.fake import plugin
import sahara.service.validation as v
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu
from sahara.utils import cluster as c_u

m = {}

_types_checks = {
    "string": [1, (), {}, True],
    "integer": ["a", (), {}, True],
    "uuid": ["z550e8400-e29b-41d4-a716-446655440000", 1, "a", (), {}, True],
    "array": [{}, 'a', 1, True],
    "boolean": [1, 'a', (), {}]
}


def _update_data(data, update):
    data.update(update)
    return data


def _get_plugins():
    fake = plugin.FakePluginProvider
    fake.name = 'fake'
    return [fake]


def _get_plugin(name):
    if name == 'fake':
        fake = plugin.FakePluginProvider
        fake.name = 'fake'
        return fake
    return None


def _get_keypair(name):
    if name != "test_keypair":
        raise nova_ex.NotFound("")


def _get_network(resource, id):
    if id != "d9a3bebc-f788-4b81-9a93-aa048022c1ca":
        raise neutron_ex.NotFound("")
    return 'OK'


def _get_fl_ip_pool_list():
    return [FakeNetwork("d9a3bebc-f788-4b81-9a93-aa048022c1ca")]


def _get_availability_zone_list(detailed=True):
    return [FakeAvailabilityZone('nova')]


def _get_heat_stack_list(**kwargs):
    if (kwargs.get('filters') and
            kwargs.get('filters').get('name') == 'test-heat'):
        return [FakeStack('test-heat')]
    return []


class FakeStack(object):
    def __init__(self, name):
        self.stack_name = name


class FakeNetwork(object):
    def __init__(self, name):
        self.name = name


class FakeAvailabilityZone(object):
    def __init__(self, name):
        self.zoneName = name


class FakeFlavor(object):
    def __init__(self, id):
        self.id = id


def _get_flavors_list():
    return [FakeFlavor("42")]


def _get_security_groups_list():
    return {'security_groups': [
            {"id": "1", "name": "default"},
            {"id": "2", "name": "group1"},
            {"id": "3", "name": "group2"}]}


def start_patch(patch_templates=True):
    get_clusters_p = mock.patch("sahara.service.api.v10.get_clusters")
    get_cluster_p = mock.patch("sahara.service.api.v10.get_cluster")
    if patch_templates:
        get_ng_templates_p = mock.patch(
            "sahara.service.api.v10.get_node_group_templates")
        get_ng_template_p = mock.patch(
            "sahara.service.api.v10.get_node_group_template")
    if patch_templates:
        get_cl_templates_p = mock.patch(
            "sahara.service.api.v10.get_cluster_templates")
        get_cl_template_p = mock.patch(
            "sahara.service.api.v10.get_cluster_template")
    nova_p = mock.patch("sahara.utils.openstack.nova.client")
    heat_p = mock.patch("sahara.utils.openstack.heat.client")
    image_manager_p = mock.patch(
        "sahara.utils.openstack.images.SaharaImageManager")
    cinder_p = mock.patch("sahara.utils.openstack.cinder.client")
    cinder_exists_p = mock.patch(
        "sahara.utils.openstack.cinder.check_cinder_exists")
    get_image_p = mock.patch("sahara.service.api.v10.get_image")

    get_image = get_image_p.start()
    get_clusters = get_clusters_p.start()
    get_cluster = get_cluster_p.start()
    if patch_templates:
        get_ng_templates = get_ng_templates_p.start()
        get_ng_template = get_ng_template_p.start()
    if patch_templates:
        get_cl_templates = get_cl_templates_p.start()
        get_cl_template_p.start()

    nova = nova_p.start()

    if patch_templates:
        get_cl_templates.return_value = []

    nova().flavors.list.side_effect = _get_flavors_list
    nova().keypairs.get.side_effect = _get_keypair
    nova().floating_ip_pools.list.side_effect = _get_fl_ip_pool_list
    nova().availability_zones.list.side_effect = _get_availability_zone_list

    neutron_p = mock.patch("sahara.utils.openstack.neutron.client")
    neutron = neutron_p.start()
    neutron().find_resource_by_id.side_effect = _get_network
    neutron().find_resource_by_id.__name__ = 'find_resource_by_id'
    neutron().list_security_groups.side_effect = _get_security_groups_list

    heat = heat_p.start()
    heat().stacks.list.side_effect = _get_heat_stack_list

    image_manager = image_manager_p.start()

    cinder = cinder_p.start()
    cinder().availability_zones.list.side_effect = _get_availability_zone_list

    cinder_exists = cinder_exists_p.start()
    cinder_exists.return_value = True

    class Image(object):
        def __init__(self, name='test'):
            self.name = name

        @property
        def id(self):
            if self.name == 'test':
                return '550e8400-e29b-41d4-a716-446655440000'
            else:
                return '813fe450-40d2-4acc-ade5-ea753a1bd5bc'

        @property
        def tags(self):
            if self.name == 'test':
                return ['fake', '0.1']
            else:
                return ['fake', 'wrong_tag']

    def _get_image(id):
        if id == '550e8400-e29b-41d4-a716-446655440000':
            return Image()
        else:
            return Image('wrong_test')

    get_image.side_effect = _get_image
    image_manager().list_registered.return_value = [Image(),
                                                    Image(name='wrong_name')]
    ng_dict = tu.make_ng_dict('ng', '42', ['namenode'], 1)
    cluster = tu.create_cluster('test', 't', 'fake', '0.1', [ng_dict],
                                id=1, status=c_u.CLUSTER_STATUS_ACTIVE)
    # stub clusters list
    get_clusters.return_value = [cluster]
    get_cluster.return_value = cluster

    # stub node templates
    if patch_templates:
        ngt_dict = {'name': 'test', 'tenant_id': 't', 'flavor_id': '42',
                    'plugin_name': 'fake', 'hadoop_version': '0.1',
                    'id': '550e8400-e29b-41d4-a716-446655440000',
                    'node_processes': ['namenode']}

        get_ng_templates.return_value = [r.NodeGroupTemplateResource(ngt_dict)]

        ct_dict = {'name': 'test', 'tenant_id': 't',
                   'plugin_name': 'fake', 'hadoop_version': '0.1'}

        get_cl_templates.return_value = [r.ClusterTemplateResource(ct_dict)]

    def _get_ng_template(id):
        for template in get_ng_templates():
            if template.id == id:
                return template
        return None

    if patch_templates:
        get_ng_template.side_effect = _get_ng_template
    # request data to validate
    patchers = [get_clusters_p, get_cluster_p,
                nova_p, get_image_p, heat_p, image_manager_p, cinder_p,
                cinder_exists_p, neutron_p]
    if patch_templates:
        patchers.extend([get_ng_template_p, get_ng_templates_p,
                         get_cl_template_p, get_cl_templates_p])
    return patchers


def stop_patch(patchers):
    for patcher in reversed(patchers):
        patcher.stop()


class ValidationTestCase(base.SaharaTestCase):
    def setUp(self):
        super(ValidationTestCase, self).setUp()
        self._create_object_fun = None
        self.scheme = None
        self.override_config('plugins', ['fake'])

    def tearDown(self):
        self._create_object_fun = None
        super(ValidationTestCase, self).tearDown()

    def _assert_calls(self, mock, call_info):
        if not call_info:
            self.assertEqual(0, mock.call_count, "Unexpected call to %s: %s"
                             % (mock.name, str(mock.call_args)))
        else:
            self.assertEqual(call_info[0], mock.call_count)
            self.assertEqual(call_info[1], mock.call_args[0][0].code)
            possible_messages = ([call_info[2]] if isinstance(
                call_info[2], six.string_types) else call_info[2])
            match = False
            check = mock.call_args[0][0].message
            if check.find('Error ID:') != -1:
                check = check.split('\n')[0]
            for message in possible_messages:
                if self._check_match(message, check):
                    match = True
                    break
            if not match:
                self.assertIn(check, possible_messages)

    def _check_match(self, expected, actual):
        d1, r1 = self._extract_printed_dict(expected)
        d2, r2 = self._extract_printed_dict(actual)

        # Note(slukjanov): regex needed because of different
        #                  versions of jsonschema generate different
        #                  messages.
        return (r1 == r2 or re.match(r1, r2)) and (d1 == d2)

    def _extract_printed_dict(self, s):
        start = s.find('{')
        if start == -1:
            return None, s

        end = s.rfind('}')
        if end == -1:
            return None, s

        return ast.literal_eval(s[start:end+1]), s[0:start+1] + s[end]

    @mock.patch("sahara.utils.api.request_data")
    @mock.patch("sahara.utils.api.bad_request")
    def _assert_create_object_validation(
            self, bad_req=None, request_data=None,
            data=None, bad_req_i=None):

        request_data.return_value = data
        # mock function that should be validated
        patchers = start_patch()
        m_func = mock.Mock()
        m_func.__name__ = "m_func"
        v.validate(self.scheme, self._create_object_fun)(m_func)(data=data)

        self.assertEqual(1, request_data.call_count)
        self._assert_calls(bad_req, bad_req_i)
        stop_patch(patchers)

    def _assert_valid_name_hostname_validation(self, data):

        data.update({'name': None})
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"name: None is not of type 'string'")
        )
        data.update({'name': ""})
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"name: '' is too short")
        )
        data.update({'name': ('a' * 51)})
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"name: '%s' is too long" % ('a' * 51))
        )
        data.update({'name': 'a-!'})
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, "VALIDATION_ERROR",
                       u"name: 'a-!' is not a 'valid_name_hostname'")
        )

    def _prop_types_str(self, prop_types):
        return ", ".join(["'%s'" % prop for prop in prop_types])

    def _assert_types(self, default_data):
        for p_name in self.scheme['properties']:
            prop = self.scheme['properties'][p_name]
            prop_types = prop["type"]
            if type(prop_types) is not list:
                prop_types = [prop_types]
            for prop_type in prop_types:
                if prop_type in _types_checks:
                    for type_ex in _types_checks[prop_type]:
                        data = default_data.copy()
                        value = type_ex
                        value_str = str(value)
                        if isinstance(value, str):
                            value_str = "'%s'" % value_str
                        data.update({p_name: value})
                        message = ("%s: %s is not of type %s" %
                                   (p_name, value_str,
                                    self._prop_types_str(prop_types)))
                        if "enum" in prop:
                            message = [message, "%s: %s is not one of %s" %
                                                (p_name, value_str,
                                                 prop["enum"])]
                        self._assert_create_object_validation(
                            data=data,
                            bad_req_i=(1, 'VALIDATION_ERROR', message)
                        )

    def _assert_cluster_configs_validation(self, require_image_id=False):
        data = {
            'name': 'test-cluster',
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'cluster_configs': {
                'HDFS': {
                    'mapreduce.task.tmp.dir': '/temp/'
                }
            },
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000'
        }
        if require_image_id:
            data_without_image = data.copy()
            data_without_image.pop('default_image_id')
            self._assert_create_object_validation(
                data=data_without_image,
                bad_req_i=(1, 'NOT_FOUND',
                           "'default_image_id' field is not found")
            )
        self._assert_create_object_validation(
            data=_update_data(data.copy(), {
                'cluster_configs': {
                    'wrong_target': {
                        'mapreduce.task.tmp.dir': '/temp/'
                    }
                }}),
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin doesn't contain applicable "
                       "target 'wrong_target'")
        )
        self._assert_create_object_validation(
            data=_update_data(data.copy(), {
                'cluster_configs': {
                    'general': {
                        's': '/temp/'
                    }
                }
            }),
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Plugin's applicable target 'general' doesn't "
                       "contain config with name 's'")
        )

    def _assert_cluster_default_image_tags_validation(self):
        data = {
            'name': 'test-cluster',
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'default_image_id': '550e8400-e29b-41d4-a716-446655440000',
            'domain_name': 'domain.org.',
            'neutron_management_network': 'd9a3bebc-f788-4b81-'
                                          '9a93-aa048022c1ca'
        }
        self._assert_create_object_validation(data=data)
        data = {
            'name': 'test-cluster',
            'plugin_name': 'fake',
            'hadoop_version': '0.1',
            'default_image_id': '813fe450-40d2-4acc-ade5-ea753a1bd5bc'
        }
        self._assert_create_object_validation(
            data=data,
            bad_req_i=(1, 'INVALID_REFERENCE',
                       "Requested image "
                       "'813fe450-40d2-4acc-ade5-ea753a1bd5bc' "
                       "doesn't contain required tags: "
                       "['0.1']"))

    def assert_protected_resource_exception(self, ex):
        self.assertIn("marked as protected", six.text_type(ex))

    def assert_created_in_another_tenant_exception(self, ex):
        self.assertIn("wasn't created in this tenant", six.text_type(ex))
