#
# Copyright (c) 2014 Mirantis Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Policy Engine For Sahara"""

import functools

from oslo_config import cfg
from oslo_policy import opts
from oslo_policy import policy

from sahara.common import policies
from sahara import context
from sahara import exceptions

ENFORCER = None

# TODO(gmann): Remove setting the default value of config policy_file
# once oslo_policy change the default value to 'policy.yaml'.
# https://opendev.org/openstack/oslo.policy/src/commit/d8534850d9238e85ae0ea55bf2ac8583681fdb2b/oslo_policy/opts.py#L49
DEFAULT_POLICY_FILE = 'policy.yaml'
opts.set_defaults(cfg.CONF, DEFAULT_POLICY_FILE)


def setup_policy():
    global ENFORCER

    ENFORCER = policy.Enforcer(cfg.CONF)
    ENFORCER.register_defaults(policies.list_rules())


def enforce(rule):
    def decorator(func):
        @functools.wraps(func)
        def handler(*args, **kwargs):
            ctx = context.ctx()
            ENFORCER.authorize(rule, {}, ctx.to_dict(), do_raise=True,
                               exc=exceptions.Forbidden)

            return func(*args, **kwargs)
        return handler

    return decorator
