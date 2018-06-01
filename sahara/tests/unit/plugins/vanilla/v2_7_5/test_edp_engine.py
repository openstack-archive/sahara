# Copyright (c) 2015 Red Hat, Inc.
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

import mock

from sahara.plugins.vanilla.v2_7_5 import edp_engine
from sahara.tests.unit import base as sahara_base
from sahara.utils import edp


class Vanilla2ConfigHintsTest(sahara_base.SaharaTestCase):
    @mock.patch(
        'sahara.plugins.vanilla.confighints_helper.'
        'get_possible_hive_config_from',
        return_value={})
    def test_get_possible_job_config_hive(
            self, get_possible_hive_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_HIVE)
        get_possible_hive_config_from.assert_called_once_with(
            'plugins/vanilla/v2_7_5/resources/hive-default.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.plugins.vanilla.hadoop2.edp_engine.EdpOozieEngine')
    def test_get_possible_job_config_java(self, BaseVanillaEdpOozieEngine):
        expected_config = {'job_config': {}}
        BaseVanillaEdpOozieEngine.get_possible_job_config.return_value = (
            expected_config)
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_JAVA)
        (BaseVanillaEdpOozieEngine.get_possible_job_config.
            assert_called_once_with(edp.JOB_TYPE_JAVA))
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.vanilla.confighints_helper.'
        'get_possible_mapreduce_config_from',
        return_value={})
    def test_get_possible_job_config_mapreduce(
            self, get_possible_mapreduce_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_MAPREDUCE)
        get_possible_mapreduce_config_from.assert_called_once_with(
            'plugins/vanilla/v2_7_5/resources/mapred-default.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.vanilla.confighints_helper.'
        'get_possible_mapreduce_config_from',
        return_value={})
    def test_get_possible_job_config_mapreduce_streaming(
            self, get_possible_mapreduce_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_MAPREDUCE_STREAMING)
        get_possible_mapreduce_config_from.assert_called_once_with(
            'plugins/vanilla/v2_7_5/resources/mapred-default.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch(
        'sahara.plugins.vanilla.confighints_helper.'
        'get_possible_pig_config_from',
        return_value={})
    def test_get_possible_job_config_pig(
            self, get_possible_pig_config_from):
        expected_config = {'job_config': {}}
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_PIG)
        get_possible_pig_config_from.assert_called_once_with(
            'plugins/vanilla/v2_7_5/resources/mapred-default.xml')
        self.assertEqual(expected_config, actual_config)

    @mock.patch('sahara.plugins.vanilla.hadoop2.edp_engine.EdpOozieEngine')
    def test_get_possible_job_config_shell(self, BaseVanillaEdpOozieEngine):
        expected_config = {'job_config': {}}
        BaseVanillaEdpOozieEngine.get_possible_job_config.return_value = (
            expected_config)
        actual_config = edp_engine.EdpOozieEngine.get_possible_job_config(
            edp.JOB_TYPE_SHELL)
        (BaseVanillaEdpOozieEngine.get_possible_job_config.
            assert_called_once_with(edp.JOB_TYPE_SHELL))
        self.assertEqual(expected_config, actual_config)
