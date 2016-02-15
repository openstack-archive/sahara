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

from sahara.plugins.ambari import health
from sahara.service.health import health_check_base
from sahara.tests.unit import base


class TestAmbariHealthCheck(base.SaharaTestCase):
    def _standard_negative_test(self, mockclient, return_value, col, count):
        mockclient.return_value = return_value
        pr = health.AlertsProvider(mock.Mock())
        service = return_value[0].get('Alert').get('service_name')
        expected_exc = health_check_base.YellowHealthError
        if col == 'RED':
            expected_exc = health_check_base.RedHealthError
        with testtools.ExpectedException(expected_exc):
            try:
                health.AmbariServiceHealthCheck(
                    mock.Mock(extra={}), pr, service).check_health()
            except Exception as e:
                self.assertEqual(
                    "Cluster health is %s. Reason: "
                    "Ambari Monitor has responded that cluster "
                    "has %s alert(s)" % (col, count), six.text_type(e))
                raise

    @mock.patch('sahara.plugins.ambari.client.AmbariClient.__init__')
    @mock.patch('sahara.plugins.ambari.client.AmbariClient.close')
    @mock.patch('sahara.plugins.ambari.client.AmbariClient.get_alerts_data')
    @mock.patch('sahara.plugins.utils.get_instance')
    def test_check_health(self, get_instance, alerts_response, close, init):
        init.return_value = None
        alerts_response.return_value = [
            {
                'Alert': {
                    'state': 'OK',
                    'service_name': 'ZOOKEEPER'
                }
            }
        ]
        result = health.AmbariServiceHealthCheck(
            mock.Mock(extra={}), health.AlertsProvider(mock.Mock()),
            'ZOOKEEPER').check_health()

        self.assertEqual('No alerts found', result)

        self._standard_negative_test(alerts_response, [
            {
                'Alert': {
                    'state': 'WARNING',
                    'service_name': 'ZOOKEEPER'
                }
            }
        ], 'YELLOW', "1 warning")

        self._standard_negative_test(alerts_response, [
            {
                'Alert': {
                    'state': 'CRITICAL',
                    'service_name': 'ZOOKEEPER'
                }
            }
        ], 'RED', "1 critical")

        # not important service: only contribute as yellow
        self._standard_negative_test(alerts_response, [
            {
                'Alert': {
                    'state': 'CRITICAL',
                    'service_name': 'Kafka'
                }
            }
        ], 'YELLOW', "1 warning")

        self._standard_negative_test(alerts_response, [
            {
                'Alert': {
                    'state': 'CRITICAL',
                    'service_name': 'ZOOKEEPER'
                },
            },
            {
                'Alert': {
                    'state': 'WARNING',
                    'service_name': 'ZOOKEEPER'
                }
            }
        ], 'RED', "1 critical and 1 warning")

        alerts_response.side_effect = [ValueError(
            "OOUCH!")]
        with testtools.ExpectedException(health_check_base.RedHealthError):
            try:
                health.AmbariHealthCheck(
                    mock.Mock(extra={}), health.AlertsProvider(mock.Mock())
                ).check_health()
            except Exception as e:
                self.assertEqual(
                    "Cluster health is RED. Reason: "
                    "Can't get response from Ambari Monitor: OOUCH!",
                    six.text_type(e))
                raise
