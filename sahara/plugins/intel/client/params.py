# Copyright (c) 2013 Intel Corporation
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

from sahara import exceptions
from sahara.plugins.intel.client import context as c


class BaseParams(c.IntelContext):
    def __init__(self, ctx, service):
        super(BaseParams, self).__init__(ctx)
        self.service = service

    def add(self, item, value, desc=''):
        data = {
            'editdesc': desc,
            'items': [
                {
                    'type': self.service,
                    'item': item,
                    'value': value,
                    'desc': desc
                }
            ]
        }

        url = '/cluster/%s/configuration' % self.cluster_name
        return self.rest.post(url, data)

    def update(self, item, value, desc='', nodes=None):
        data = {
            'editdesc': desc,
            'items': [
                {
                    'type': self.service,
                    'item': item,
                    'value': value
                }
            ]
        }
        if nodes:
            data = {
                'editdesc': desc,
                'items': map(lambda node: {
                    'type': self.service,
                    'item': item,
                    'value': value,
                    'hostname': node
                }, nodes)
            }

        url = '/cluster/%s/configuration' % self.cluster_name
        return self.rest.put(url, data)

    def get(self, hosts, item):
        raise exceptions.NotImplementedException("BaseParams.get")


class Params(c.IntelContext):
    def __init__(self, ctx, is_yarn_supported):
        super(Params, self).__init__(ctx)
        self.hadoop = BaseParams(self, 'hadoop')
        self.hdfs = BaseParams(self, 'hdfs')
        if is_yarn_supported:
            self.yarn = BaseParams(self, 'yarn')
        else:
            self.mapred = BaseParams(self, 'mapred')
        self.oozie = BaseParams(self, 'oozie')
