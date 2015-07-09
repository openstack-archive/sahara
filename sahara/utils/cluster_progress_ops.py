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

from oslo_config import cfg
from oslo_utils import excutils
from oslo_utils import timeutils
import six

from sahara import conductor as c
from sahara.conductor import resource
from sahara import context
from sahara.utils import cluster as cluster_utils

conductor = c.API
CONF = cfg.CONF

event_log_opts = [
    cfg.BoolOpt('disable_event_log',
                default=False,
                help="Disables event log feature.")
]


CONF.register_opts(event_log_opts)


def add_successful_event(instance):
    if CONF.disable_event_log:
        return

    cluster_id = instance.cluster_id
    step_id = get_current_provisioning_step(cluster_id)
    if step_id:
        conductor.cluster_event_add(context.ctx(), step_id, {
            'successful': True,
            'node_group_id': instance.node_group_id,
            'instance_id': instance.instance_id,
            'instance_name': instance.instance_name,
            'event_info': None,
        })


def add_fail_event(instance, exception):
    if CONF.disable_event_log:
        return

    cluster_id = instance.cluster_id
    step_id = get_current_provisioning_step(cluster_id)
    event_info = six.text_type(exception)

    if step_id:
        conductor.cluster_event_add(context.ctx(), step_id, {
            'successful': False,
            'node_group_id': instance.node_group_id,
            'instance_id': instance.instance_id,
            'instance_name': instance.instance_name,
            'event_info': event_info,
        })


def add_provisioning_step(cluster_id, step_name, total):
    if (CONF.disable_event_log or
            not cluster_utils.check_cluster_exists(cluster_id)):
        return

    prev_step = get_current_provisioning_step(cluster_id)
    if prev_step:
        conductor.cluster_provision_step_update(context.ctx(), prev_step)

    step_type = context.ctx().current_instance_info.step_type
    new_step = conductor.cluster_provision_step_add(
        context.ctx(), cluster_id, {
            'step_name': step_name,
            'step_type': step_type,
            'total': total,
            'started_at': timeutils.utcnow(),
        })
    context.current().current_instance_info.step_id = new_step
    return new_step


def get_current_provisioning_step(cluster_id):
    if (CONF.disable_event_log or
            not cluster_utils.check_cluster_exists(cluster_id)):
        return None
    current_instance_info = context.ctx().current_instance_info
    return current_instance_info.step_id


def event_wrapper(mark_successful_on_exit, **spec):
    """"General event-log wrapper

    :param mark_successful_on_exit: should we send success event
    after execution of function

    :param spec: extra specification
    :parameter step: provisioning step name (only for provisioning
    steps with only one event)
    :parameter param: tuple (name, pos) with parameter specification,
    where 'name' is the name of the parameter of function, 'pos' is the
    position of the parameter of function. This parameter is used to
    extract info about Instance or Cluster.
    """

    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            if CONF.disable_event_log:
                return func(*args, **kwargs)
            step_name = spec.get('step', None)
            instance = _find_in_args(spec, *args, **kwargs)
            cluster_id = instance.cluster_id

            if not cluster_utils.check_cluster_exists(cluster_id):
                return func(*args, **kwargs)

            if step_name:
                # It's single process, let's add provisioning step here
                add_provisioning_step(cluster_id, step_name, 1)

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


def _get_info_from_instance(arg):
    if isinstance(arg, resource.InstanceResource):
        return arg
    return None


def _get_info_from_cluster(arg):
    if isinstance(arg, resource.ClusterResource):
        return context.InstanceInfo(arg.id)
    return None


def _get_event_info(arg):
    try:
        return arg.get_event_info()
    except AttributeError:
        return None


def _get_info_from_obj(arg):
    functions = [_get_info_from_instance, _get_info_from_cluster,
                 _get_event_info]

    for func in functions:
        value = func(arg)
        if value:
            return value
    return None


def _find_in_args(spec, *args, **kwargs):
    param_values = spec.get('param', None)

    if param_values:
        p_name, p_pos = param_values
        obj = kwargs.get(p_name, None)
        if obj:
            return _get_info_from_obj(obj)
        return _get_info_from_obj(args[p_pos])

    # If param is not specified, let's search instance in args

    for arg in args:
        val = _get_info_from_instance(arg)
        if val:
            return val

    for arg in kwargs.values():
        val = _get_info_from_instance(arg)
        if val:
            return val

    # If instance not found in args, let's get instance info from context

    return context.ctx().current_instance_info
