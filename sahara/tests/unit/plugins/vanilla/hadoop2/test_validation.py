# Copyright (c) 2014 Mirantis Inc.
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

import testtools

from sahara.plugins import exceptions as ex
from sahara.plugins.vanilla import plugin as p
from sahara.tests.unit import base
from sahara.tests.unit import testutils as tu


class ValidationTest(base.SaharaTestCase):
    def setUp(self):
        super(ValidationTest, self).setUp()
        self.pl = p.VanillaProvider()

    def test_validate(self):
        self.ng = []
        self.ng.append(tu.make_ng_dict("nn", "f1", ["namenode"], 0))
        self.ng.append(tu.make_ng_dict("sn", "f1", ["secondarynamenode"], 0))
        self.ng.append(tu.make_ng_dict("jt", "f1", ["resourcemanager"], 0))
        self.ng.append(tu.make_ng_dict("tt", "f1", ["nodemanager"], 0))
        self.ng.append(tu.make_ng_dict("dn", "f1", ["datanode"], 0))
        self.ng.append(tu.make_ng_dict("hs", "f1", ["historyserver"], 0))
        self.ng.append(tu.make_ng_dict("oo", "f1", ["oozie"], 0))

        self._validate_case(1, 1, 1, 10, 10, 0, 0)
        self._validate_case(1, 0, 1, 1, 4, 0, 0)
        self._validate_case(1, 1, 1, 0, 3, 0, 0)
        self._validate_case(1, 0, 1, 0, 3, 0, 0)
        self._validate_case(1, 1, 0, 0, 3, 0, 0)
        self._validate_case(1, 0, 1, 1, 3, 1, 1)
        self._validate_case(1, 1, 1, 1, 3, 1, 0)

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(0, 0, 1, 10, 3, 0, 0)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(2, 0, 1, 10, 3, 0, 0)

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 2, 1, 1, 3, 1, 1)

        with testtools.ExpectedException(ex.RequiredServiceMissingException):
            self._validate_case(1, 0, 0, 10, 3, 0, 0)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 0, 2, 10, 3, 0, 0)

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 0, 1, 1, 3, 2, 1)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 0, 1, 1, 3, 1, 2)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 1, 1, 0, 2, 0, 0)
        with testtools.ExpectedException(ex.RequiredServiceMissingException):
            self._validate_case(1, 0, 1, 1, 3, 0, 1)
        with testtools.ExpectedException(ex.RequiredServiceMissingException):
            self._validate_case(1, 0, 1, 0, 3, 1, 1)
        with testtools.ExpectedException(ex.RequiredServiceMissingException):
            self._validate_case(1, 0, 1, 1, 0, 1, 1)

        cl = self._create_cluster(
            1, 1, 1, 0, 3, 0, 0,
            cluster_configs={'HDFS': {'dfs.replication': 4}})

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self.pl.validate(cl)

        self.ng.append(tu.make_ng_dict("hi", "f1", ["hiveserver"], 0))
        self.ng.append(tu.make_ng_dict("sh", "f1",
                                       ["spark history server"], 0))

        self._validate_case(1, 1, 0, 0, 3, 0, 0, 1, 0)
        self._validate_case(1, 1, 0, 0, 3, 0, 0, 0, 1)

        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 1, 0, 0, 3, 0, 0, 2, 0)
        with testtools.ExpectedException(ex.InvalidComponentCountException):
            self._validate_case(1, 1, 0, 0, 3, 0, 0, 0, 2)

    def _create_cluster(self, *args, **kwargs):
        lst = []
        for i in range(0, len(args)):
            self.ng[i]['count'] = args[i]
            lst.append(self.ng[i])

        return tu.create_cluster("cluster1", "tenant1", "vanilla",
                                 "2.7.1", lst, **kwargs)

    def _validate_case(self, *args):
        cl = self._create_cluster(*args)

        self.pl.validate(cl)
