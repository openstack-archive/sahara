# Copyright 2012 New Dream Network, LLC (DreamHost)
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
from unittest import mock

import testscenarios
import testtools

from sahara.db.migration import cli


class TestCli(testtools.TestCase):
    func_name = ''
    exp_args = ()
    exp_kwargs = {}

    scenarios = [
        ('stamp',
         dict(argv=['prog', 'stamp', 'foo'], func_name='stamp',
              exp_args=('foo',), exp_kwargs={'sql': False})),
        ('stamp-sql',
         dict(argv=['prog', 'stamp', 'foo', '--sql'], func_name='stamp',
              exp_args=('foo',), exp_kwargs={'sql': True})),
        ('current',
         dict(argv=['prog', 'current'], func_name='current',
              exp_args=[], exp_kwargs=dict())),
        ('history',
         dict(argv=['prog', 'history'], func_name='history',
              exp_args=[], exp_kwargs=dict())),
        ('check_migration',
         dict(argv=['prog', 'check_migration'], func_name='branches',
              exp_args=[], exp_kwargs=dict())),
        ('sync_revision_autogenerate',
         dict(argv=['prog', 'revision', '--autogenerate', '-m', 'message'],
              func_name='revision',
              exp_args=(),
              exp_kwargs={
                  'message': 'message', 'sql': False, 'autogenerate': True})),
        ('sync_revision_sql',
         dict(argv=['prog', 'revision', '--sql', '-m', 'message'],
              func_name='revision',
              exp_args=(),
              exp_kwargs={
                  'message': 'message', 'sql': True, 'autogenerate': False})),
        ('upgrade-sql',
         dict(argv=['prog', 'upgrade', '--sql', 'head'],
              func_name='upgrade',
              exp_args=('head',),
              exp_kwargs={'sql': True})),

        ('upgrade-delta',
         dict(argv=['prog', 'upgrade', '--delta', '3'],
              func_name='upgrade',
              exp_args=('+3',),
              exp_kwargs={'sql': False}))
    ]

    def setUp(self):
        super(TestCli, self).setUp()
        do_alembic_cmd_p = mock.patch.object(cli, 'do_alembic_command')
        self.addCleanup(do_alembic_cmd_p.stop)
        self.do_alembic_cmd = do_alembic_cmd_p.start()
        self.addCleanup(cli.CONF.reset)

    def test_cli(self):
        with mock.patch.object(sys, 'argv', self.argv):
            cli.main()
            self.do_alembic_cmd.assert_has_calls(
                [mock.call(
                    mock.ANY, self.func_name,
                    *self.exp_args, **self.exp_kwargs)]
            )


def load_tests(loader, in_tests, pattern):
    return testscenarios.load_tests_apply_scenarios(loader, in_tests, pattern)
