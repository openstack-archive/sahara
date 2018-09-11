# Copyright (c) 2018 Red Hat, Inc.
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

from sahara import context


def ctx(**kwargs):
    return context.ctx()


def set_ctx(new_ctx, **kwargs):
    context.set_ctx(new_ctx)


def has_ctx(**kwargs):
    return context.has_ctx()


def sleep(seconds=0, **kwargs):
    context.sleep(seconds)


def current(**kwargs):
    return context.current()


def set_current_instance_id(instance_id, **kwargs):
    return context.set_current_instance_id(instance_id)


class PluginsThreadGroup(context.ThreadGroup):

    def __init__(self, thread_pool_size=1000, **kwargs):
        super(PluginsThreadGroup, self).__init__()


class PluginsContext(context.Context):

    def __init__(self,
                 user_id=None,
                 tenant_id=None,
                 auth_token=None,
                 service_catalog=None,
                 username=None,
                 tenant_name=None,
                 roles=None,
                 is_admin=None,
                 remote_semaphore=None,
                 resource_uuid=None,
                 current_instance_info=None,
                 request_id=None,
                 auth_plugin=None,
                 overwrite=True,
                 **kwargs):

        super(PluginsContext, self).__init__(auth_token=auth_token,
                                             user=user_id,
                                             tenant=tenant_id,
                                             is_admin=is_admin,
                                             resource_uuid=resource_uuid,
                                             request_id=request_id,
                                             roles=roles, **kwargs)
