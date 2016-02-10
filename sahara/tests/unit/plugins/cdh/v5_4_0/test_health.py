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
import testtools

from sahara.plugins.cdh.v5_4_0 import health
from sahara.service.health import health_check_base as base_health
from sahara.tests.unit import base as unit_base


class TestHealthCheck(unit_base.SaharaTestCase):
    def test_check_health_availability(self):
        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.3.0')
        self.assertFalse(health.CDH540HealthCheck(cluster).is_available())

        cluster = mock.Mock(plugin_name='cdh', hadoop_version='5.4.0')
        self.assertTrue(health.CDH540HealthCheck(cluster).is_available())

    @mock.patch('sahara.plugins.cdh.health.CDHHealthCheck.get_cloudera_health')
    def test_health_calculation(self, cdh_response):
        cdh_response.return_value = {
            'yarn01': {
                'summary': 'GOOD',
            },
            'hdfs01': {
                'summary': 'GOOD',
            }
        }
        cluster = mock.Mock()
        self.assertEqual('All services are healthy',
                         health.CDH540HealthCheck(cluster).check_health())

        cdh_response.return_value = {
            'yarn01': {
                'summary': 'BAD',
            },
            'hdfs01': {
                'summary': 'GOOD',
            }
        }

        with testtools.ExpectedException(base_health.RedHealthError):
            health.CDH540HealthCheck(cluster).check_health()

        cdh_response.return_value = {
            'yarn01': {
                'summary': 'CONCERNING',
            },
            'hdfs01': {
                'summary': 'GOOD',
            }
        }

        with testtools.ExpectedException(base_health.YellowHealthError):
            health.CDH540HealthCheck(cluster).check_health()

        cdh_response.return_value = {
            'yarn01': {
                'summary': 'GOOD',
            },
            'hdfs01': {
                'summary': 'GOOD',
            },
            'some_service01': {
                'summary': 'BAD'
            }
        }
        with testtools.ExpectedException(base_health.YellowHealthError):
            health.CDH540HealthCheck(cluster).check_health()

        cdh_response.return_value = {
            'yarn01': {
                'summary': 'UNEXPECTED_STATE',
            },
            'hdfs01': {
                'summary': 'GOOD',
            },
            'some_service01': {
                'summary': 'BAD'
            }
        }
        with testtools.ExpectedException(base_health.RedHealthError):
            health.CDH540HealthCheck(cluster).check_health()
