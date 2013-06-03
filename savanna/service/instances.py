# Copyright (c) 2013 Mirantis Inc.
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

from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def create_cluster(cluster):
    try:
        _create_instances(cluster)
        _await_instances(cluster)
        _configure_instances(cluster)
    except Exception as ex:
        LOG.warn("Can't start cluster: %s", ex)
        _rollback_cluster_creation(cluster, ex)


def _create_instances(cluster):
    """Create all instances using nova client and persist them into DB."""
    pass


def _await_instances(cluster):
    """Await all instances are in Active status and available."""
    pass


def _configure_instances(cluster):
    """Configure active instances.

    * generate /etc/hosts
    * setup passwordless login
    * etc.
    """
    pass


def _rollback_cluster_creation(cluster, ex):
    """Shutdown all instances and update cluster status."""
    # update cluster status
    # update cluster status description
    _shutdown_instances(cluster, True)


def _shutdown_instances(cluster, quiet=False):
    """Shutdown all instances related to the specified cluster."""
    pass


def shutdown_cluster(cluster):
    """Shutdown specified cluster and all related resources."""
    pass
