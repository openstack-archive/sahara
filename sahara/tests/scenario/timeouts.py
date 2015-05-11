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


class Defaults(object):
    def __init__(self, config):
        self.timeout_check_transient = config.get('timeout_check_transient',
                                                  300)
        self.timeout_delete_resource = config.get('timeout_delete_resource',
                                                  300)
        self.timeout_poll_cluster_status = config.get(
            'timeout_poll_cluster_status', 1800)
        self.timeout_poll_jobs_status = config.get('timeout_poll_jobs_status',
                                                   1800)

    @classmethod
    def init_defaults(cls, config):
        if not hasattr(cls, 'instance'):
            cls.instance = Defaults(config)
        return cls.instance
