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

from __future__ import print_function

from oslo_config import cfg


DataProcessingGroup = [
    cfg.IntOpt('cluster_timeout',
               default=3600,
               help='Timeout (in seconds) to wait for cluster deployment.'),
    cfg.IntOpt('request_timeout',
               default=10,
               help='Timeout (in seconds) between status checks.'),
    cfg.StrOpt('fake_image_id',
               help='ID of an image which is used for cluster creation.'),
    cfg.StrOpt('saharaclient_version',
               default='1.1',
               help='Version of python-saharaclient'),
    cfg.StrOpt('sahara_url',
               help='Sahara url as http://ip:port/api_version/tenant_id'),
]
