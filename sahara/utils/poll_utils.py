# Copyright (c) 2015 Mirantis Inc.
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
from oslo_log import log as logging
from oslo_utils import timeutils

from sahara import context
from sahara import exceptions as ex
from sahara.utils import cluster as cluster_utils

LOG = logging.getLogger(__name__)

# set 3 hours timeout by default
DEFAULT_TIMEOUT = 10800
DEFAULT_SLEEP_TIME = 5

timeouts_opts = [
    # engine opts
    cfg.IntOpt('ips_assign_timeout',
               default=DEFAULT_TIMEOUT,
               help="Assign IPs timeout, in seconds"),
    cfg.IntOpt('wait_until_accessible',
               default=DEFAULT_TIMEOUT,
               help="Wait for instance accessibility, in seconds"),

    # direct engine opts
    cfg.IntOpt('delete_instances_timeout',
               default=DEFAULT_TIMEOUT,
               help="Wait for instances to be deleted, in seconds"),

    # volumes opts
    cfg.IntOpt(
        'detach_volume_timeout', default=300,
        help='Timeout for detaching volumes from instance, in seconds'),
]

timeouts = cfg.OptGroup(name='timeouts',
                        title='Sahara timeouts')

CONF = cfg.CONF
CONF.register_group(timeouts)
CONF.register_opts(timeouts_opts, group=timeouts)


def _get_consumed(started_at):
    return timeutils.delta_seconds(started_at, timeutils.utcnow())


def _get_current_value(cluster, option):
    option_target = option.applicable_target
    conf = cluster.cluster_configs
    if option_target in conf and option.name in conf[option_target]:
        return conf[option_target][option.name]
    return option.default_value


def poll(get_status, kwargs=None, args=None, operation_name=None,
         timeout_name=None, timeout=DEFAULT_TIMEOUT, sleep=DEFAULT_SLEEP_TIME,
         exception_strategy='raise'):
    """This util poll status of object obj during some timeout.

    :param get_status: function, which return current status of polling
    as Boolean
    :param kwargs: keyword arguments of function get_status
    :param operation_name: name of polling process
    :param timeout_name: name of timeout option
    :param timeout: value of timeout in seconds. By default, it equals to
    3 hours
    :param sleep: duration between two consecutive executions of
    get_status function
    :param exception_strategy: possible values ('raise', 'mark_as_true',
    'mark_as_false'). If exception_strategy is 'raise' exception would be
    raised. If exception_strategy is 'mark_as_true', return value of
    get_status would marked as True, and in case of 'mark_as_false' - False.
    By default it's 'raise'.
    """
    start_time = timeutils.utcnow()
    # We shouldn't raise TimeoutException if incorrect timeout specified and
    # status is ok now. In such way we should execute get_status at least once.
    at_least_once = True
    if not kwargs:
        kwargs = {}
    if not args:
        args = ()

    while at_least_once or _get_consumed(start_time) < timeout:
        at_least_once = False
        try:
            status = get_status(*args, **kwargs)
        except BaseException:
            if exception_strategy == 'raise':
                raise
            elif exception_strategy == 'mark_as_true':
                status = True
            else:
                status = False

        if status:
            operation = "Operation"
            if operation_name:
                operation = "Operation with name {op_name}".format(
                    op_name=operation_name)
            LOG.debug(
                '{operation_desc} was executed successfully in timeout '
                '{timeout}'
                .format(operation_desc=operation, timeout=timeout))
            return

        context.sleep(sleep)
    raise ex.TimeoutException(timeout, operation_name, timeout_name)


def plugin_option_poll(cluster, get_status, option, operation_name, sleep_time,
                       kwargs):

    def _get(n_cluster, n_kwargs):
        if not cluster_utils.check_cluster_exists(n_cluster):
            return True
        return get_status(**n_kwargs)

    poll_description = {
        'get_status': _get,
        'kwargs': {'n_cluster': cluster, 'n_kwargs': kwargs},
        'timeout': _get_current_value(cluster, option),
        'operation_name': operation_name,
        'sleep': sleep_time,
        'timeout_name': option.name
    }

    poll(**poll_description)


def poll_status(option, operation_name, sleep):
    def decorator(f):
        @functools.wraps(f)
        def handler(*args, **kwargs):
            poll_description = {
                'get_status': f,
                'kwargs': kwargs,
                'args': args,
                'timeout': getattr(CONF.timeouts, option),
                'operation_name': operation_name,
                'timeout_name': option,
                'sleep': sleep,
            }
            poll(**poll_description)
        return handler
    return decorator
