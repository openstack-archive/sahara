# Copyright (c) 2016 Mirantis Inc.
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
import six
import testtools

from sahara.plugins.cdh import health
from sahara.service.health import health_check_base as base_health
from sahara.tests.unit import base as unit_base


class TestHealthCheck(unit_base.SaharaTestCase):
    def test_check_health_availability(self):
        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.3.0')
        self.assertFalse(health.ClouderaManagerHealthCheck(
            cluster, mock.Mock()).is_available())
        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.4.0')
        self.assertTrue(health.ClouderaManagerHealthCheck(
            cluster, mock.Mock()).is_available())
        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.5.0')
        self.assertTrue(health.ClouderaManagerHealthCheck(
            cluster, mock.Mock()).is_available())

        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.3.0')
        self.assertFalse(health.ServiceHealthCheck(
            cluster, mock.Mock(), mock.Mock()).is_available())
        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.4.0')
        self.assertTrue(health.ServiceHealthCheck(
            cluster, mock.Mock(), mock.Mock()).is_available())
        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.5.0')
        self.assertTrue(health.ServiceHealthCheck(
            cluster, mock.Mock(), mock.Mock()).is_available())

    def _base_negative_testcase(self, cdh_response_mock, return_value, msg,
                                col, service, postfix=None):
        if not postfix:
            postfix = ""
        cdh_response_mock.return_value = return_value
        exc = (base_health.YellowHealthError
               if col == 'YELLOW' else base_health.RedHealthError)
        with testtools.ExpectedException(exc):
            try:
                pr = health.HealthStatusProvider(mock.Mock(), mock.Mock())
                health.ServiceHealthCheck(
                    mock.Mock(), provider=pr, service=service).check_health()
            except Exception as e:
                msg = "%s%s" % (msg, postfix)
                all_message = "Cluster health is %(col)s. Reason: %(msg)s" % {
                    'col': col, 'msg': msg}
                self.assertEqual(all_message, six.text_type(e))
                raise

    @mock.patch('sahara.plugins.cdh.health.HealthStatusProvider.'
                'get_cloudera_health')
    @mock.patch('sahara.plugins.cdh.health.HealthStatusProvider.'
                'get_important_services')
    def test_health_calculation(self, important_stuff, cdh_response):
        important_stuff.return_value = ['yarn01', 'hdfs01', 'oozie01']
        cdh_response.return_value = {
            'yarn01': {
                'summary': 'GOOD',
            },
            'hdfs01': {
                'summary': 'GOOD',
            }
        }
        msg = ("Cloudera Manager has responded that service is in "
               "the %s state")
        pr = health.HealthStatusProvider(mock.Mock(), mock.Mock())
        self.assertEqual(
            msg % 'GOOD', health.ServiceHealthCheck(
                mock.Mock(), provider=pr, service='hdfs01').check_health())

        self._base_negative_testcase(cdh_response, {
            'yarn01': {'summary': 'GOOD'},
            'hdfs01': {'summary': 'BAD'}
        }, msg % 'BAD', 'RED', service='hdfs01')

        self._base_negative_testcase(cdh_response, {
            'yarn01': {'summary': 'CONCERNING'},
            'hdfs01': {'summary': 'BAD'}
        }, msg % 'CONCERNING', 'YELLOW', service='yarn01')

        # not important service, only yellow health
        self._base_negative_testcase(cdh_response, {
            'yarn01': {'summary': 'CONCERNING'},
            'hdfs01': {'summary': 'BAD'},
            'some_service01': {'summary': 'BAD'}
        }, msg % 'BAD', 'YELLOW', service='some_service01')

        self._base_negative_testcase(cdh_response, {
            'yarn01': {'summary': 'UNKNOWN_STATE'},
            'hdfs01': {'summary': 'BAD'},
            'some_service01': {'summary': 'BAD'}
        }, msg % 'UNKNOWN_STATE', 'RED', service='yarn01')

        # test additional info
        postfix = (". The following checks did not "
                   "pass: SUPER_HEALTH_CHECK - BAD state")
        self._base_negative_testcase(cdh_response, {
            'yarn01': {'summary': 'UNKNOWN_STATE'},
            'hdfs01': {'summary': 'BAD', 'checks': [
                {'name': 'SUPER_HEALTH_CHECK', 'summary': 'BAD'}]},
            'some_service01': {'summary': 'BAD'}
        }, msg % 'BAD', 'RED', service='hdfs01', postfix=postfix)
