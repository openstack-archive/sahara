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

"""Handles database requests from other savanna services."""

# from savanna.openstack.common.rpc import common as rpc_common
from savanna.db_new import base as db_base


class ConductorManager(db_base.Base):
    """This class aimed to conduct things.

    The methods in the base API for savanna-conductor are various proxy
    operations that allows other services to get specific work done without
    locally accessing the database.
    """

    def __init__(self):
        super(ConductorManager, self).__init__()

    def cluster_get(self, context, cluster):
        """Return the cluster or None if it does not exist."""
        return self.db.cluster_get(context, cluster)

    def cluster_get_all(self, context):
        """Get all clusters."""
        return self.db.cluster_get_all(context)

    def cluster_create(self, context, values):
        """Create a cluster from the values dictionary."""
        return self.db.cluster_create(context, values)

    def cluster_update(self, context, cluster, values):
        """Set the given properties on cluster and update it."""
        return self.db.cluster_update(context, cluster, values)

    def cluster_destroy(self, context, cluster):
        """Destroy the cluster or raise if it does not exist."""
        return self.db.cluster_destroy(context, cluster)
