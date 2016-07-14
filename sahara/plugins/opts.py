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

# File contains plugins opts to avoid cyclic imports issue

from oslo_config import cfg

opts = [
    cfg.ListOpt('plugins',
                default=['vanilla', 'spark', 'cdh', 'ambari', 'storm', 'mapr'],
                help='List of plugins to be loaded. Sahara preserves the '
                     'order of the list when returning it.'),
]

CONF = cfg.CONF
CONF.register_opts(opts)
