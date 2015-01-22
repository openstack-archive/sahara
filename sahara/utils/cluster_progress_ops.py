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

import functools

from oslo.utils import excutils
from oslo.utils import timeutils
import six

from sahara import conductor as c
from sahara.conductor import resource
from sahara import context
from sahara import exceptions
from sahara.i18n import _

conductor = c.API


def add_successful_event(instance):
    cluster_id = instance.node_group.cluster_id
    step_id = get_current_provisioning_step(cluster_id)
    if step_id:
        conductor.cluster_event_add(context.ctx(), step_id, {
            'successful': True,
            'node_group_id': instance.node_group_id,
            'instance_id': instance.id,
            'instance_name': instance.instance_name,
            'event_info': None,
        })


def add_fail_event(instance, exception):
    cluster_id = instance.node_group.cluster_id
    step_id = get_current_provisioning_step(cluster_id)
    event_info = six.text_type(exception)

    if step_id:
        conductor.cluster_event_add(context.ctx(), step_id, {
            'successful': False,
            'node_group_id': instance.node_group_id,
            'instance_id': instance.id,
            'instance_name': instance.instance_name,
            'event_info': event_info,
        })


def add_provisioning_step(cluster_id, step_name, total):
    update_provisioning_steps(cluster_id)
    return conductor.cluster_provision_step_add(context.ctx(), cluster_id, {
        'step_name': step_name,
        'completed': 0,
        'total': total,
        'started_at': timeutils.utcnow(),
    })


def get_current_provisioning_step(cluster_id):
    update_provisioning_steps(cluster_id)
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    for step in cluster.provision_progress:
        if step.successful is not None:
            continue

        return step.id

    return None


def update_provisioning_steps(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)

    for step in cluster.provision_progress:
        if step.successful is not None:
            continue

        has_failed = False
        successful_events_count = 0
        events = conductor.cluster_provision_step_get_events(
            ctx, step.id)
        for event in events:
            if event.successful:
                successful_events_count += 1
            else:
                has_failed = True

        successful = None
        if has_failed:
            successful = False
        elif successful_events_count == step.total:
            successful = True

        completed_at = None
        if successful and not step.completed_at:
            completed_at = timeutils.utcnow()

        conductor.cluster_provision_step_update(ctx, step.id, {
            'completed': successful_events_count,
            'successful': successful,
            'completed_at': completed_at,
        })

        if successful:
            conductor.cluster_provision_step_remove_events(
                ctx, step.id)


def get_cluster_events(cluster_id, provision_step=None):
    update_provisioning_steps(cluster_id)
    if provision_step:
        return conductor.cluster_provision_step_get_events(
            context.ctx(), provision_step)
    else:
        cluster = conductor.cluster_get(context.ctx(), cluster_id)
        events = []
        for step in cluster['provision_progress']:
            step_id = step['id']
            events += conductor.cluster_provision_step_get_events(
                context.ctx(), step_id)
        return events


def event_wrapper(mark_successful_on_exit):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            # NOTE (vgridnev): We should know information about instance,
            #                  so we should find instance in args or kwargs.
            #                  Also, we import sahara.conductor.resource
            #                  to check some object is Instance

            instance = None
            for arg in args:
                if isinstance(arg, resource.InstanceResource):
                    instance = arg

            for kw_arg in kwargs.values():
                if isinstance(kw_arg, resource.InstanceResource):
                    instance = kw_arg

            if instance is None:
                raise exceptions.InvalidDataException(
                    _("Function should have an Instance as argument"))

            try:
                value = func(*args, **kwargs)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    add_fail_event(instance, e)

            if mark_successful_on_exit:
                add_successful_event(instance)

            return value
        return handler
    return decorator


def event_wrapper_without_instance(mark_successful_on_exit):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            ctx = context.ctx()
            (cluster_id, instance_id, instance_name,
                node_group_id) = ctx.current_instance_info
            step_id = get_current_provisioning_step(cluster_id)

            try:
                value = func(*args, **kwargs)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    conductor.cluster_event_add(
                        context.ctx(),
                        step_id, {
                            'successful': False,
                            'node_group_id': node_group_id,
                            'instance_id': instance_id,
                            'instance_name': instance_name,
                            'event_info': six.text_type(e),
                        })

            if mark_successful_on_exit:
                conductor.cluster_event_add(
                    context.ctx(),
                    step_id, {
                        'successful': True,
                        'node_group_id': node_group_id,
                        'instance_id': instance_id,
                        'instance_name': instance_name,
                    })

            return value
        return handler
    return decorator
