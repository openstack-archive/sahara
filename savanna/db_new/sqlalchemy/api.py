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

"""Implementation of SQLAlchemy backend."""

import sys

import sqlalchemy as sa

from savanna.db_new.sqlalchemy import models as m
from savanna.openstack.common.db import exception as db_exc
from savanna.openstack.common.db.sqlalchemy import session as db_session
from savanna.openstack.common import log as logging


LOG = logging.getLogger(__name__)

get_engine = db_session.get_engine
get_session = db_session.get_session


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def model_query(model, context, session=None, project_only=None):
    """Query helper.

    :param model: base model to query
    :param context: context to query under
    :param project_only: if present and context is user-type, then restrict
            query to match the context's project_id.
    """
    session = session or get_session()

    query = session.query(model)

    if project_only:
        query = query.filter_by(tenant_id=context.project_id)

    return query


def setup_db():
    try:
        engine = db_session.get_engine(sqlite_fk=True)
        m.Cluster.metadata.create_all(engine)
    except sa.exc.OperationalError as e:
        LOG.error("Database registration exception: %s", e)
        return False
    return True


def drop_db():
    try:
        engine = db_session.get_engine(sqlite_fk=True)
        m.Cluster.metadata.drop_all(engine)
    except Exception as e:
        LOG.error("Database shutdown exception: %s", e)
        return False
    return True


## Helpers for building constraints / equality checks


def constraint(**conditions):
    return Constraint(conditions)


def equal_any(*values):
    return EqualityCondition(values)


def not_equal(*values):
    return InequalityCondition(values)


class Constraint(object):
    def __init__(self, conditions):
        self.conditions = conditions

    def apply(self, model, query):
        for key, condition in self.conditions.iteritems():
            for clause in condition.clauses(getattr(model, key)):
                query = query.filter(clause)
        return query


class EqualityCondition(object):
    def __init__(self, values):
        self.values = values

    def clauses(self, field):
        return sa.or_([field == value for value in self.values])


class InequalityCondition(object):
    def __init__(self, values):
        self.values = values

    def clauses(self, field):
        return [field != value for value in self.values]


## Cluster ops


def _cluster_get(context, session, cluster_id):
    query = model_query(m.Cluster, context, session)
    return query.filter_by(id=cluster_id).first()


def cluster_get(context, cluster_id):
    return _cluster_get(context, get_session(), cluster_id)


def cluster_get_all(context):
    query = model_query(m.Cluster, context)
    return query.all()


def cluster_create(context, values):
    cluster = m.Cluster()
    cluster.update(values)

    try:
        cluster.save()
    except db_exc.DBDuplicateEntry as e:
        # raise exception about duplicated columns (e.columns)
        raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return cluster


def cluster_update(context, cluster_id, values):
    session = get_session()
    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)
        cluster.update(values)
        cluster.save(session=session)


def cluster_destroy(context, cluster_id):
    session = get_session()
    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)

        if not cluster:
            # raise not found error
            raise RuntimeError("Cluster not found!")

        session.delete(cluster)
