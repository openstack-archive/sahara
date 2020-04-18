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


from unittest import mock

from oslo_utils import uuidutils

from sahara import conductor
from sahara import context
from sahara.tests.unit import base
from sahara.tests.unit.conductor import test_api
from sahara.utils import cluster_progress_ops as cpo


class FakeInstance(object):
    def __init__(self):
        self.id = uuidutils.generate_uuid()
        self.name = uuidutils.generate_uuid()
        self.cluster_id = uuidutils.generate_uuid()
        self.node_group_id = uuidutils.generate_uuid()
        self.instance_id = uuidutils.generate_uuid()
        self.instance_name = uuidutils.generate_uuid()


class ClusterProgressOpsTest(base.SaharaWithDbTestCase):
    def setUp(self):
        super(ClusterProgressOpsTest, self).setUp()
        self.api = conductor.API

    def _make_sample(self):
        ctx = context.ctx()
        cluster = self.api.cluster_create(ctx, test_api.SAMPLE_CLUSTER)
        return ctx, cluster

    def test_update_provisioning_steps(self):
        ctx, cluster = self._make_sample()

        step_id1 = self.api.cluster_provision_step_add(ctx, cluster.id, {
            "step_name": "some_name1",
            "total": 2,
        })

        self.api.cluster_event_add(ctx, step_id1, {
            "event_info": "INFO",
            "successful": True
        })

        self.api.cluster_provision_progress_update(ctx, cluster.id)

        # check that we have correct provision step

        result_cluster = self.api.cluster_get(ctx, cluster.id)
        result_step = result_cluster.provision_progress[0]

        self.assertIsNone(result_step.successful)

        # check updating in case of successful provision step

        self.api.cluster_event_add(ctx, step_id1, {
            "event_info": "INFO",
            "successful": True
        })

        self.api.cluster_provision_progress_update(ctx, cluster.id)

        result_cluster = self.api.cluster_get(ctx, cluster.id)
        result_step = result_cluster.provision_progress[0]

        self.assertTrue(result_step.successful)

        # check updating in case of failed provision step

        step_id2 = self.api.cluster_provision_step_add(ctx, cluster.id, {
            "step_name": "some_name1",
            "total": 2,
        })

        self.api.cluster_event_add(ctx, step_id2, {
            "event_info": "INFO",
            "successful": False,
        })

        self.api.cluster_provision_progress_update(ctx, cluster.id)

        result_cluster = self.api.cluster_get(ctx, cluster.id)

        for step in result_cluster.provision_progress:
            if step.id == step_id2:
                self.assertFalse(step.successful)

        # check that it's possible to add provision step after failed step
        step_id3 = cpo.add_provisioning_step(cluster.id, "some_name", 2)

        self.assertEqual(
            step_id3, cpo.get_current_provisioning_step(cluster.id))

    def test_get_cluster_events(self):
        ctx, cluster = self._make_sample()

        step_id1 = self.api.cluster_provision_step_add(ctx, cluster.id, {
            'step_name': "some_name1",
            'total': 3,
        })
        step_id2 = self.api.cluster_provision_step_add(ctx, cluster.id, {
            'step_name': "some_name",
            'total': 2,
        })

        self.api.cluster_event_add(ctx, step_id1, {
            "event_info": "INFO",
            'successful': True,
        })

        self.api.cluster_event_add(ctx, step_id2, {
            "event_info": "INFO",
            'successful': True,
        })
        cluster = self.api.cluster_get(context.ctx(), cluster.id, True)
        for step in cluster.provision_progress:
            self.assertEqual(1, len(step.events))

    def _make_checks(self, instance_info, sleep=True):
        ctx = context.ctx()

        if sleep:
            context.sleep(2)

        current_instance_info = ctx.current_instance_info
        self.assertEqual(instance_info, current_instance_info)

    def test_instance_context_manager(self):
        fake_instances = [FakeInstance() for _ in range(50)]

        # check that InstanceContextManager works fine sequentially

        for instance in fake_instances:
            info = context.InstanceInfo(
                None, instance.id, instance.name, None)
            with context.InstanceInfoManager(info):
                self._make_checks(info, sleep=False)

        # check that InstanceContextManager works fine in parallel

        with context.ThreadGroup() as tg:
            for instance in fake_instances:
                info = context.InstanceInfo(
                    None, instance.id, instance.name, None)
                with context.InstanceInfoManager(info):
                    tg.spawn("make_checks", self._make_checks, info)

    @cpo.event_wrapper(True)
    def _do_nothing(self):
        pass

    @mock.patch('sahara.utils.cluster_progress_ops._find_in_args')
    @mock.patch('sahara.utils.cluster.check_cluster_exists')
    def test_event_wrapper(self, p_check_cluster_exists, p_find):
        self.override_config("disable_event_log", True)
        self._do_nothing()

        self.assertEqual(0, p_find.call_count)

        self.override_config("disable_event_log", False)
        p_find.return_value = FakeInstance()
        p_check_cluster_exists.return_value = False
        self._do_nothing()

        self.assertEqual(1, p_find.call_count)
        self.assertEqual(1, p_check_cluster_exists.call_count)

    def test_cluster_get_with_events(self):
        ctx, cluster = self._make_sample()

        step_id = cpo.add_provisioning_step(cluster.id, "Some name", 3)
        self.api.cluster_event_add(ctx, step_id, {
            'event_info': "INFO", 'successful': True})
        cluster = self.api.cluster_get(ctx, cluster.id, True)

        steps = cluster.provision_progress
        step = steps[0]
        self.assertEqual("Some name", step.step_name)
        self.assertEqual(3, step.total)
        self.assertEqual("INFO", step.events[0].event_info)

    @mock.patch('sahara.context.ctx')
    @mock.patch(
        'sahara.utils.cluster_progress_ops.get_current_provisioning_step',
        return_value='step_id')
    @mock.patch('sahara.utils.cluster_progress_ops.conductor')
    def test_add_successful_event(self, conductor, get_step, ctx):
        instance = FakeInstance()

        self.override_config("disable_event_log", True)
        cpo.add_successful_event(instance)
        self.assertEqual(0, conductor.cluster_event_add.call_count)

        self.override_config("disable_event_log", False)
        cpo.add_successful_event(instance)
        self.assertEqual(1, conductor.cluster_event_add.call_count)
        args, kwargs = conductor.cluster_event_add.call_args
        self.assertEqual('step_id', args[1])
        req_dict = {
            'successful': True,
            'node_group_id': instance.node_group_id,
            'instance_id': instance.instance_id,
            'instance_name': instance.instance_name,
            'event_info': None,
        }
        self.assertEqual(req_dict, args[2])

    @mock.patch('sahara.context.ctx')
    @mock.patch(
        'sahara.utils.cluster_progress_ops.get_current_provisioning_step',
        return_value='step_id')
    @mock.patch('sahara.utils.cluster_progress_ops.conductor')
    def test_add_fail_event(self, conductor, get_step, ctx):
        instance = FakeInstance()

        self.override_config("disable_event_log", True)
        cpo.add_fail_event(instance, Exception('oops'))
        self.assertEqual(0, conductor.cluster_event_add.call_count)

        self.override_config("disable_event_log", False)
        cpo.add_fail_event(instance, Exception('oops'))
        self.assertEqual(1, conductor.cluster_event_add.call_count)
        args, kwargs = conductor.cluster_event_add.call_args
        self.assertEqual('step_id', args[1])
        req_dict = {
            'successful': False,
            'node_group_id': instance.node_group_id,
            'instance_id': instance.instance_id,
            'instance_name': instance.instance_name,
            'event_info': 'oops',
        }
        self.assertEqual(req_dict, args[2])
