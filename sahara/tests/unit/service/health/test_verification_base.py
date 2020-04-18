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

from unittest import mock

import six
import testtools

from sahara import conductor
from sahara import context
from sahara import exceptions
from sahara.plugins import health_check_base
from sahara.service.health import verification_base
from sahara.tests.unit import base
from sahara.tests.unit.conductor import test_api


class Check(health_check_base.BasicHealthCheck):
    def check_health(self):
        return "No criminality"

    def get_health_check_name(self):
        return "James bond check"

    def is_available(self):
        return True


class RedCheck(Check):
    def check_health(self):
        raise health_check_base.RedHealthError("Ooouch!")


class YellowCheck(Check):
    def check_health(self):
        raise health_check_base.YellowHealthError("No problems, boss!")


class TestVerifications(base.SaharaWithDbTestCase):
    def setUp(self):
        super(TestVerifications, self).setUp()
        self.api = conductor.API

    def _cluster_sample(self):
        ctx = context.ctx()
        cluster = self.api.cluster_create(ctx, test_api.SAMPLE_CLUSTER)
        return cluster

    @testtools.skip("Story 2007450 - http://sqlalche.me/e/bhk3")
    @mock.patch('sahara.plugins.health_check_base.get_health_checks')
    def test_verification_start(self, get_health_checks):
        cluster = self._cluster_sample()
        get_health_checks.return_value = [Check]
        verification_base.handle_verification(cluster, {
            'verification': {'status': 'START'}})
        cluster = self.api.cluster_get(context.ctx(), cluster)
        ver = cluster.verification
        self.assertEqual('GREEN', ver['status'])
        self.assertEqual(1, len(ver['checks']))

        self.assertEqual('No criminality', ver.checks[0]['description'])
        id = ver['id']

        get_health_checks.return_value = [YellowCheck, Check, Check]

        verification_base.handle_verification(cluster, {
            'verification': {'status': 'START'}})
        cluster = self.api.cluster_get(context.ctx(), cluster)
        ver = cluster.verification

        self.assertEqual('YELLOW', ver['status'])
        self.assertEqual(3, len(ver['checks']))
        self.assertNotEqual(ver['id'], id)

        get_health_checks.return_value = [RedCheck, YellowCheck]

        verification_base.handle_verification(cluster, {
            'verification': {'status': 'START'}})
        cluster = self.api.cluster_get(context.ctx(), cluster)
        ver = cluster.verification

        self.assertEqual('RED', ver['status'])
        self.assertEqual(2, len(ver['checks']))
        self.assertNotEqual(ver['id'], id)
        self.assertEqual("James bond check", ver['checks'][0]['name'])

    def _validate_exception(self, exc, expected_message):
        message = six.text_type(exc)
        # removing Error ID
        message = message.split('\n')[0]
        self.assertEqual(expected_message, message)

    @testtools.skip("Story 2007450 - http://sqlalche.me/e/bhk3")
    def test_conductor_crud_verifications(self):
        ctx = context.ctx()
        try:
            self.api.cluster_verification_add(
                ctx, '1', values={'status': 'name'})
        except exceptions.NotFoundException as e:
            self._validate_exception(e, "Cluster id '1' not found!")

        cl = self._cluster_sample()
        ver = self.api.cluster_verification_add(
            ctx, cl.id, values={'status': 'GREAT!'})
        ver = self.api.cluster_verification_get(ctx, ver['id'])
        self.assertEqual('GREAT!', ver['status'])

        self.api.cluster_verification_update(ctx, ver['id'],
                                             values={'status': "HEY!"})
        ver = self.api.cluster_verification_get(ctx, ver['id'])
        self.assertEqual('HEY!', ver['status'])
        self.assertIsNone(
            self.api.cluster_verification_delete(ctx, ver['id']))

        try:
            self.api.cluster_verification_delete(ctx, ver['id'])
        except exceptions.NotFoundException as e:
            self._validate_exception(
                e, "Verification id '%s' not found!" % ver['id'])
        try:
            self.api.cluster_verification_update(
                ctx, ver['id'], values={'status': "ONE MORE"})
        except exceptions.NotFoundException as e:
            self._validate_exception(
                e, "Verification id '%s' not found!" % ver['id'])

        self.assertIsNone(self.api.cluster_verification_get(ctx, ver['id']))

    @testtools.skip("Story 2007450 - http://sqlalche.me/e/bhk3")
    def test_conductor_crud_health_checks(self):
        ctx = context.ctx()
        try:
            self.api.cluster_health_check_add(
                ctx, '1', values={'status': 'status'})
        except exceptions.NotFoundException as e:
            self._validate_exception(e, "Verification id '1' not found!")

        cl = self._cluster_sample()
        vid = self.api.cluster_verification_add(
            ctx, cl.id, values={'status': 'GREAT!'})['id']

        hc = self.api.cluster_health_check_add(ctx, vid, {'status': "Sah"})
        hc = self.api.cluster_health_check_get(ctx, hc['id'])
        self.assertEqual('Sah', hc['status'])

        hc = self.api.cluster_health_check_update(
            ctx, hc['id'], {'status': "ara"})
        hc = self.api.cluster_health_check_get(ctx, hc['id'])
        self.assertEqual('ara', hc['status'])

        self.api.cluster_verification_delete(ctx, vid)
        try:
            hc = self.api.cluster_health_check_update(
                ctx, hc['id'], {'status': "rulez!"})
        except exceptions.NotFoundException as e:
            self._validate_exception(
                e, "Health check id '%s' not found!" % hc['id'])

        self.assertIsNone(self.api.cluster_health_check_get(ctx, hc['id']))
