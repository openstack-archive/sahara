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


import sqlalchemy as sa

from savanna import context
from savanna.db import model_base as mb
from savanna.tests.unit import base


class TestModel(mb.SavannaBase, mb.IdMixin):
    test_field = sa.Column(sa.String(80))


def _insert_test_object():
    t = TestModel()
    t.test_field = 123
    context.model_save(t)

    return t


class ModelHelpersTest(base.DbTestCase):
    def test_model_save(self):
        self.assertEqual(0, len(context.model_query(TestModel).all()))

        t = _insert_test_object()

        self.assertEqual(1, len(context.model_query(TestModel).all()))

        db_t = context.model_query(TestModel).first()

        self.assertEqual(t.id, db_t.id)
        self.assertEqual(t.test_field, db_t.test_field)

    def test_model_update(self):
        _insert_test_object()

        t = context.current().session.query(TestModel).first()

        context.model_update(t, test_field=42)

        db_t = context.model_query(TestModel).first()

        self.assertEqual(t.id, db_t.id)
        self.assertEqual(42, db_t.test_field)
