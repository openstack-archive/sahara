# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import sahara.utils.configs as c

import six


class AttrDict(dict):

    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

node_domain = None


class Cluster(AttrDict):
    fields = ['id', 'name', 'description', 'tenant_id', 'trust_id',
              'is_transient', 'plugin_name', 'hadoop_version',
              'cluster_configs', 'default_image_id', 'anti_affinity',
              'management_private_key', 'management_public_key',
              'user_keypair_id', 'status', 'status_description', 'info',
              'extra', 'node_groups', 'cluster_template_id',
              'cluster_template']

    def __init__(self, mapping=None, **kwargs):
        self.id = None
        self.cluster_template_id = None
        self.cluster_template = None
        self.node_groups = []
        d = dict((f, None) for f in Cluster.fields)
        if mapping:
            d.update(mapping)
        if kwargs:
            d.update(kwargs)
        AttrDict.__init__(self, d)
        if self.node_groups:
            for ng in self.node_groups:
                ng.cluster_id = self.id
                ng.cluster = self
                ng.cluster_template_id = self.cluster_template_id
                ng.cluster_template = self.cluster_template


class NodeGroup(AttrDict):
    fields = ['id', 'name', 'flavor_id', 'image_id', 'image_username',
              'node_processes', 'node_configs', 'volumes_per_node',
              'volumes_size', 'volume_mount_prefix', 'floating_ip_pool',
              'count', 'instances', 'node_group_template_id',
              'node_group_template', 'cluster_id', 'cluster',
              'cluster_template_id', 'cluster_template']

    def __init__(self, mapping=None, **kwargs):
        self.id = None
        self.instances = []
        d = dict((f, None) for f in NodeGroup.fields)
        if mapping:
            d.update(mapping)
        if kwargs:
            d.update(kwargs)
        AttrDict.__init__(self, d)
        if self.instances:
            for i in self.instances:
                i.node_group_id = self.id
                i.node_group = self

    def configuration(self):
        return c.merge_configs(self.cluster.cluster_configs, self.node_configs)

    def storage_paths(self):
        mp = [self.volume_mount_prefix + str(idx)
              for idx in range(1, self.volumes_per_node + 1)]
        if not mp:
            mp = ['/mnt']
        return mp

    def get_image_id(self):
        return self.image_id or self.cluster.default_image_id


class Instance(AttrDict):
    fields = ['id', 'node_group_id', 'node_group', 'instance_id',
              'instance_name', 'internal_ip', 'management_ip', 'volumes']

    def __init__(self, mapping=None, **kwargs):
        d = dict((f, None) for f in Instance.fields)
        p = lambda i: i[0] in Instance.fields
        if mapping:
            d.update(dict(filter(p, six.iteritems(mapping))))
        if kwargs:
            d.update(dict(filter(p, six.iteritems(kwargs))))
        AttrDict.__init__(self, d)
        results = kwargs['results'] if 'results' in kwargs else []
        default_result = (kwargs['default_result']
                          if 'default_result' in kwargs
                          else Remote.DEFAULT_RESULT)
        self._remote = Remote(results, default_result)

    def hostname(self):
        return self.instance_name

    def fqdn(self):
        return self.instance_name + '.' + node_domain

    def remote(self):
        return self._remote


class Remote(object):
    DEFAULT_RESULT = (0, '', '')

    def __init__(self, results=[], default_result=None):
        self.fs = []
        self.history = []
        self.results = results
        self.default_result = (default_result
                               if default_result
                               else Remote.DEFAULT_RESULT)

    def register_result(self, command, result):
        result += [(command, result)]

    def get_result(self, command):
        for r_command, result in self.results:
            if r_command == command:
                return result
        return (self.default_result
                if command['get_stderr']
                else self.default_result[:-1])

    def __exit__(self, *args):
        pass

    def __enter__(self):
        return self

    def write_file_to(self, remote_file, data, run_as_root=False, timeout=120):
        self.fs += [{'file': remote_file, 'data': data, 'root': run_as_root,
                     'timeout': timeout}]

    def write_files_to(self, files, run_as_root=False, timeout=120):
        self.fs += [{'file': f, 'data': d, 'root': run_as_root,
                     'timeout': timeout}
                    for f, d in six.iteritems(files)]

    def read_file_from(self, remote_file, run_as_root=False, timeout=120):
        for f in self.fs:
            if f['file'] == remote_file:
                return f['data']
        return None

    def replace_remote_string(self, remote_file, old_str,
                              new_str, timeout=120):
        pass

    def get_neutron_info(self):
        return

    def get_http_client(self, port, info=None):
        return

    def close_http_sessions(self):
        pass

    def execute_command(self, cmd, run_as_root=False, get_stderr=False,
                        raise_when_error=True, timeout=300):
        command = {'cmd': cmd,
                   'run_as_root': run_as_root,
                   'get_stderr': get_stderr,
                   'raise_when_error': raise_when_error,
                   'timeout': timeout}
        self.history += [command]
        return self.get_result(command)
