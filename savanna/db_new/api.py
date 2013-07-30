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

"""Defines interface for DB access.

Functions in this module are imported into the savanna.db namespace. Call these
functions from savanna.db namespace, not the savanna.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface.

**Related Flags**

:db_backend:  string to lookup in the list of LazyPluggable backends.
              `sqlalchemy` is the only supported backend right now.

:sql_connection:  string specifying the sqlalchemy connection to use, like:
                  `sqlite:///var/lib/savanna/savanna.sqlite`.

"""

from oslo.config import cfg

from savanna.openstack.common.db import api as db_api
from savanna.openstack.common import log as logging


CONF = cfg.CONF

_BACKEND_MAPPING = {
    'sqlalchemy': 'savanna.db.sqlalchemy.api',
}

IMPL = db_api.DBAPI(backend_mapping=_BACKEND_MAPPING)
LOG = logging.getLogger(__name__)


## Helpers for building constraints / equality checks


def constraint(**conditions):
    """Return a constraint object suitable for use with some updates."""
    return IMPL.constraint(**conditions)


def equal_any(*values):
    """Return an equality condition object suitable for use in a constraint.

    Equal_any conditions require that a model object's attribute equal any
    one of the given values.
    """
    return IMPL.equal_any(*values)


def not_equal(*values):
    """Return an inequality condition object suitable for use in a constraint.

    Not_equal conditions require that a model object's attribute differs from
    all of the given values.
    """
    return IMPL.not_equal(*values)


## Cluster ops


def cluster_get(context, cluster_id):
    return IMPL.cluster_get(context, cluster_id)


def cluster_get_all(context):
    return IMPL.cluster_get_all(context)


def cluster_create(context, values):
    return IMPL.cluster_create(context, values)


def cluster_update(context, cluster_id, values):
    return IMPL.cluster_update(context, cluster_id, values)


def cluster_destroy(context, cluster_id):
    return IMPL.cluster_destroy(context, cluster_id)
