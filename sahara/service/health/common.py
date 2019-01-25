# Copyright (c) 2016 Mirantis Inc.
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

from oslo_config import cfg

HEALTH_STATUS_GREEN = "GREEN"
HEALTH_STATUS_YELLOW = "YELLOW"
HEALTH_STATUS_RED = "RED"
HEALTH_STATUS_CHECKING = "CHECKING"
HEALTH_STATUS_DONE = [
    HEALTH_STATUS_GREEN,
    HEALTH_STATUS_YELLOW,
    HEALTH_STATUS_RED,
]

VERIFICATIONS_START_OPS = "START"

VERIFICATIONS_OPS = [
    VERIFICATIONS_START_OPS,
]

CONF = cfg.CONF

health_opts = [
    cfg.BoolOpt('verification_enable', default=True,
                help="Option to enable verifications for all clusters"),
    cfg.IntOpt('verification_periodic_interval', default=600,
               help="Interval between two consecutive periodic tasks for "
                    "verifications, in seconds."),
    cfg.IntOpt('verification_timeout', default=600,
               help="Time limit for health check function, in seconds.")
]
health_opts_group = cfg.OptGroup(
    'cluster_verifications', title='Options to configure verifications')
CONF.register_group(group=health_opts_group)
CONF.register_opts(health_opts, group=health_opts_group)
