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


from sahara import conductor
from sahara import context
from sahara.plugins.ambari import common
from sahara.plugins import exceptions as ex
from sahara.plugins import utils


conductor = conductor.API


def validate_creation(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    _check_ambari(cluster)


def _check_ambari(cluster):
    count = utils.get_instances_count(cluster, common.AMBARI_SERVER)
    if count != 1:
        raise ex.InvalidComponentCountException(common.AMBARI_SERVER, 1, count)
