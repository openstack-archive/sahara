# Copyright (c) 2013 Hortonworks, Inc.
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

import pkg_resources as pkg

from sahara.plugins.hdp import clusterspec as cs
from sahara import version


class TestServer(object):
    def __init__(self, hostname, role, img, flavor, public_ip, private_ip):
        self.inst_fqdn = hostname
        self.role = role
        self.instance_info = InstanceInfo(
            hostname, img, flavor, public_ip, private_ip)
        self.management_ip = public_ip
        self.public_ip = public_ip
        self.internal_ip = private_ip
        self.node_group = None

    def fqdn(self):
        return self.inst_fqdn

    def remote(self):
        return None


def get_instance_info(*args, **kwargs):
    return args[0].instance_info


def create_clusterspec(hdp_version='1.3.2'):
    version_suffix = hdp_version.replace('.', '_')
    cluster_config_file = pkg.resource_string(
        version.version_info.package,
        'plugins/hdp/versions/version_{0}/resources/'
        'default-cluster.template'.format(version_suffix))

    return cs.ClusterSpec(cluster_config_file, version=hdp_version)


class InstanceInfo(object):
    def __init__(self, hostname, image, flavor, management_ip, internal_ip):
        self.image = image
        self.flavor = flavor
        self.management_ip = management_ip
        self.internal_ip = internal_ip


class TestCluster(object):
    def __init__(self, node_groups, cluster_configs=None):
        self.plugin_name = 'hdp'
        self.hadoop_version = None
        if cluster_configs:
            self.cluster_configs = cluster_configs
        else:
            self.cluster_configs = {}
        self.node_groups = node_groups
        self.default_image_id = '11111'


class TestNodeGroup(object):
    def __init__(self, name, instances, node_processes, count=1):
        self.name = name
        self.instances = instances
        if instances:
            for i in instances:
                i.node_group = self
        self.node_processes = node_processes
        self.count = count
        self.id = name
        self.ng_storage_paths = []

    def storage_paths(self):
        return self.ng_storage_paths


class TestUserInputConfig(object):
    def __init__(self, tag, target, name):
        self.tag = tag
        self.applicable_target = target
        self.name = name


class TestRequest(object):
    def put(self, url, data=None, auth=None, headers=None):
        self.url = url
        self.data = data
        self.auth = auth
        self.headers = headers
        self.method = 'put'

        return TestResult(200)

    def post(self, url, data=None, auth=None, headers=None):
        self.url = url
        self.data = data
        self.auth = auth
        self.headers = headers
        self.method = 'post'

        return TestResult(201)

    def delete(self, url, auth=None, headers=None):
        self.url = url
        self.auth = auth
        self.data = None
        self.headers = headers
        self.method = 'delete'

        return TestResult(200)


class TestResult(object):
    def __init__(self, status):
        self.status_code = status
        self.text = ''


class TestUserInput(object):
    def __init__(self, config, value):
        self.config = config
        self.value = value
