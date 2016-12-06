# Copyright (c) 2015 Mirantis Inc.
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

from sahara.tests.unit import base
from sahara.utils import resources


class SimpleResourceTestCase(base.SaharaTestCase):

    def setUp(self):
        super(SimpleResourceTestCase, self).setUp()
        self.test_name = "test_res"
        self.test_info_0 = {"a": "a"}
        self.test_info_1 = {"b": "b"}

    def test_resource_init_attrs(self):
        r = resources.Resource(_name=self.test_name, _info=self.test_info_0)
        r.b = "b"

        self.assertEqual("a", r.a)
        self.assertEqual("b", r.__getattr__("b"))
        self.assertIn("b", r.__dict__)

        self.assertEqual(self.test_info_0, r._info)
        self.assertEqual(self.test_name, r._name)
        self.assertEqual(self.test_name, r.__resource_name__)

    def test_resource_to_dict(self):
        r = resources.Resource(_name=self.test_name, _info=self.test_info_0)

        self.assertEqual(self.test_info_0, r.to_dict())
        self.assertEqual({self.test_name: self.test_info_0}, r.wrapped_dict)

    def test_resource_eq(self):
        r0 = resources.Resource(_name=self.test_name, _info=self.test_info_0)
        r1 = resources.Resource(_name=self.test_name, _info=self.test_info_1)

        self.assertNotEqual(r0, r1)

    def test_as_resource(self):
        r = resources.Resource(_name=self.test_name, _info=self.test_info_0)
        self.assertEqual(r, r.as_resource())

    def test_repr(self):
        r = resources.Resource(_name=self.test_name, _info=self.test_info_0)

        dict_repr = self.test_info_0.__repr__()
        self.assertEqual("<test_res %s>" % dict_repr, r.__repr__())


class InheritedBaseResourceTestCase(base.SaharaTestCase):

    def test_to_dict_no_filters(self):
        class A(resources.BaseResource):
            __filter_cols__ = []

        test_a = A()
        test_a.some_attr = "some_value"
        a_dict = test_a.to_dict()

        self.assertEqual({"some_attr": "some_value"}, a_dict)

    def test_to_dict_with_filters_and_sa(self):
        class A(resources.BaseResource):
            __filter_cols__ = ["filtered"]

        test_a = A()
        test_a.some_attr = "some_value"
        test_a.filtered = "something_hidden"
        test_a._sa_instance_state = "some_sqlalchemy_magic"
        a_dict = test_a.to_dict()

        self.assertEqual({"some_attr": "some_value"}, a_dict)
