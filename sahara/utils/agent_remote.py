# Copyright (c) 2013 Mirantis Inc.
# Copyright (c) 2013 Hortonworks, Inc.
# Copyright (c) 2013 Eric Larson
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
import logging
import pickle
import string

from oslo.config import cfg
from oslo import messaging
import requests

from sahara.openstack.common import timeutils
from sahara.utils import files
from sahara.utils import remote


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def _log_runtime(func):
    def handle(self, *args, **kwargs):
        s_time = timeutils.utcnow()
        try:
            return func(self, *args, **kwargs)
        finally:
            run_time = timeutils.delta_seconds(s_time, timeutils.utcnow())
            _log_command(self.instance_name,
                         '%s took %.1f seconds to complete' %
                         (func.__name__, run_time))

    return handle


def _log_command(instance_name, msg):
        LOG.debug('[%s] [guest-agent] %s' % (instance_name, msg))


# TODO(dmitryme): once requests in requirements are >= 2.1,
# replace that self-made serialization with pickling. Specifically,
# we wait for the following commit:
# https://github.com/kennethreitz/requests/commit/512beb8
class _ResponseObject(requests.Response):
    """A substitute for requests.Response object."""

    def setstate(self, state):
        for name, value in state.items():
            setattr(self, name, value)

        # pickled objects do not have .raw
        setattr(self, '_content_consumed', True)


def _deserialize_http_response(func):
    @functools.wraps(func)
    def handle(*args, **kwargs):
        resp = _ResponseObject()
        result = func(*args, **kwargs)
        resp.setstate(pickle.loads(result))
        return resp

    return handle


def _log_and_deserialize_http_request(request_type):
    def decorator(func):
        def handle(self, url, *args, **kwargs):
            _log_command(self.instance_name, 'Performing %s request to %s' %
                                             (request_type, url))

            func_decorated = _deserialize_http_response(func)
            func_decorated = _log_runtime(func_decorated)

            return func_decorated(self, url, *args, **kwargs)

        return handle

    return decorator


class _Requests(object):
    """A proxy for requests library."""

    def __init__(self, client, instance_name):
        self._client = client
        self.instance_name = instance_name

    @_log_and_deserialize_http_request('GET')
    def get(self, url, timeout=300, **kwargs):
        client = self._client.prepare(timeout=timeout)
        return client.call({}, 'request', http_method='get', url=url,
                               kwargs=kwargs)

    @_log_and_deserialize_http_request('POST')
    def post(self, url, data=None, timeout=300, **kwargs):
        client = self._client.prepare(timeout=timeout)
        kwargs['data'] = data
        return client.call({}, 'request', http_method='post', url=url,
                               kwargs=kwargs)

    @_log_and_deserialize_http_request('PUT')
    def put(self, url, data=None, timeout=300, **kwargs):
        client = self._client.prepare(timeout=timeout)
        kwargs['data'] = data
        return client.call({}, 'request', http_method='put', url=url,
                               kwargs=kwargs)

    @_log_and_deserialize_http_request('DELETE')
    def delete(self, url, timeout=300, **kwargs):
        client = self._client.prepare(timeout=timeout)
        return client.call({}, 'request', http_method='delete', url=url,
                               kwargs=kwargs)


class _InstanceInteropHelper(remote.Remote):

    def __init__(self, transport, instance):
        self.instance_name = instance.instance_name
        target = messaging.Target(topic='sahara-topic', version='1.0',
                                  server=instance.instance_name)
        self._client = messaging.RPCClient(transport, target)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass

    def get_neutron_info(self):
        return {}

    def get_http_client(self, port, info=None):
        return _Requests(self._client, self.instance_name)

    def close_http_sessions(self):
        # we have nothing to close
        pass

    @_log_runtime
    def execute_command(self, cmd, run_as_root=False, get_stderr=False,
                        raise_when_error=True, timeout=300):
        _log_command(self.instance_name, 'Executing "%s"' % cmd)

        client = self._client.prepare(timeout=timeout)
        return client.call({}, 'execute_command', cmd=cmd,
                           run_as_root=run_as_root, get_stderr=get_stderr,
                           raise_when_error=raise_when_error)

    @_log_runtime
    def write_file_to(self, remote_file, data, run_as_root=False, timeout=120):
        _log_command(self.instance_name, 'Writing file "%s"' % remote_file)

        client = self._client.prepare(timeout=timeout)
        client.call({}, 'write_files_to', files={remote_file: data},
                        run_as_root=run_as_root)

    @_log_runtime
    def write_files_to(self, files, run_as_root=False, timeout=120):
        _log_command(self.instance_name, 'Writing files "%s"' % files.keys())

        client = self._client.prepare(timeout=timeout)
        client.call({}, 'write_files_to', files=files, run_as_root=run_as_root)

    @_log_runtime
    def read_file_from(self, remote_file, run_as_root=False, timeout=120):
        _log_command(self.instance_name, 'Reading file "%s"' % remote_file)

        client = self._client.prepare(timeout=timeout)
        return client.call({}, 'read_file_from', remote_file=remote_file,
                               run_as_root=run_as_root)

    @_log_runtime
    def replace_remote_string(self, remote_file, old_str, new_str,
                              timeout=120):
        _log_command(self.instance_name, 'In file "%s" replacing string "%s" '
                     'with "%s"' % (remote_file, old_str, new_str))

        old_str = old_str.replace("\'", "\''")
        new_str = new_str.replace("\'", "\''")

        replace_str = "'s,%s,%s,g' %s" % (old_str, new_str, remote_file)
        cmd = "sed -i %s" % replace_str

        client = self._client.prepare(timeout=timeout)
        client.call({}, 'execute_command', cmd=cmd, get_stderr=False,
                    run_as_root=True, raise_when_error=True)


class AgentRemoteDriver(remote.RemoteDriver):
    def setup_remote(self, engine):
        if not CONF.rpc_server_host:
            LOG.critical('A valid "rpc_server_host" parameter must be '
                         'supplied in config file for Agent remote.')
            raise RuntimeError('Invalid rpc_server_host supplied in config')

        self.transport = messaging.get_transport(cfg.CONF)
        self.rabbitmq_userdata = files.get_file_text(
            'resources/userdata.rabbitmq.template')

    def get_remote(self, instance):
        return _InstanceInteropHelper(self.transport, instance)

    def get_userdata_template(self):
        userdata_template = string.Template(self.rabbitmq_userdata)
        return userdata_template.safe_substitute(
            rpc_server_host=CONF.rpc_server_host)
