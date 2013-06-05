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
from savanna.db import models as m
from savanna.tests.unit.db.models import base as models_test_base


class ClusterModelTest(models_test_base.ModelTestCase):
    def testCreateCluster(self):
        session = ctx.current().session
        with session.begin():
            c = m.Cluster('c-1', 't-1', 'p-1', 'hv-1')
            session.add(c)

        with session.begin():
            res = session.query(m.Cluster).filter_by().first()

            self.assertIsValidModelObject(res)

    def testCreateClusterFromDict(self):
        c = m.Cluster('c-1', 't-1', 'p-1', 'hv-1')
        c_dict = c.dict
        del c_dict['created']
        del c_dict['updated']
        del c_dict['id']
        del c_dict['node_groups']
        del c_dict['status']
        del c_dict['status_description']

        c_dict.update({
            'tenant_id': 't-1'
        })
        self.assertEqual(self.get_clean_dict(c),
                         self.get_clean_dict(m.Cluster(**c_dict)))
