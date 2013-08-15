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

from savanna.db.sqlalchemy import models as m
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


def column_query(context, *columns, **kwargs):
    session = kwargs.get("session") or get_session()

    query = session.query(*columns)

    if kwargs.get("project_only"):
        query = query.filter_by(tenant_id=context.tenant_id)

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
    values = values.copy()
    cluster = m.Cluster()
    node_groups = values.pop("node_groups", [])
    cluster.update(values)

    session = get_session()
    with session.begin():
        try:
            cluster.save(session=session)
            for ng in node_groups:
                node_group = m.NodeGroup()
                node_group.update({"cluster_id": cluster.id})
                node_group.update(ng)
                node_group.save(session=session)

        except db_exc.DBDuplicateEntry as e:
            # raise exception about duplicated columns (e.columns)
            raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return cluster_get(context, cluster.id)


def cluster_update(context, cluster_id, values):
    session = get_session()

    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)
        cluster.update(values)
        cluster.save(session=session)

    return cluster_get(context, cluster_id)


def cluster_destroy(context, cluster_id):
    session = get_session()
    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)

        if not cluster:
            # raise not found error
            raise RuntimeError("Cluster not found!")

        session.delete(cluster)


## Node Group ops

def _node_group_get(context, session, node_group_id):
    query = model_query(m.NodeGroup, context, session)
    return query.filter_by(id=node_group_id).first()


def node_group_add(context, cluster_id, values):
    session = get_session()

    with session.begin():
        node_group = m.NodeGroup()
        node_group.update({"cluster_id": cluster_id})
        node_group.update(values)
        node_group.save(session=session)

    return node_group.id


def node_group_update(context, node_group_id, values):
    session = get_session()
    with session.begin():
        node_group = _node_group_get(context, session, node_group_id)
        node_group.update(values)
        node_group.save(session=session)


def node_group_remove(context, node_group_id):
    session = get_session()
    with session.begin():
        node_group = _node_group_get(context, session, node_group_id)

        if not node_group:
            # raise not found error
            raise RuntimeError("Node Group not found!")

        session.delete(node_group)


## Instance ops

def _instance_get(context, session, instance_id):
    query = model_query(m.Instance, context, session)
    return query.filter_by(id=instance_id).first()


def instance_add(context, node_group_id, values):
    session = get_session()

    with session.begin():
        instance = m.Instance()
        instance.update({"node_group_id": node_group_id})
        instance.update(values)
        instance.save(session=session)

        node_group = _node_group_get(context, session, node_group_id)
        node_group.count += 1
        node_group.save(session=session)

    return instance.id


def instance_update(context, instance_id, values):
    session = get_session()
    with session.begin():
        instance = _instance_get(context, session, instance_id)
        instance.update(values)
        instance.save(session=session)


def instance_remove(context, instance_id):
    session = get_session()
    with session.begin():
        instance = _instance_get(context, session, instance_id)

        if not instance:
            # raise not found error
            raise RuntimeError("Instance not found!")

        session.delete(instance)

        node_group_id = instance.node_group_id
        node_group = _node_group_get(context, session, node_group_id)
        node_group.count -= 1
        node_group.save(session=session)


## Cluster Template ops

def _cluster_template_get(context, session, cluster_template_id):
    query = model_query(m.ClusterTemplate, context, session)
    return query.filter_by(id=cluster_template_id).first()


def cluster_template_get(context, cluster_template_id):
    return _cluster_template_get(context, get_session(), cluster_template_id)


def cluster_template_get_all(context):
    query = model_query(m.ClusterTemplate, context)
    return query.all()


def cluster_template_create(context, values):
    values = values.copy()
    cluster_template = m.ClusterTemplate()
    node_groups = values.pop("node_groups", [])
    cluster_template.update(values)

    session = get_session()
    with session.begin():
        try:
            cluster_template.save(session=session)
            for ng in node_groups:
                node_group = m.TemplatesRelation()
                node_group.update({"cluster_template_id": cluster_template.id})
                node_group.update(ng)
                node_group.save(session=session)

        except db_exc.DBDuplicateEntry as e:
            # raise exception about duplicated columns (e.columns)
            raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return cluster_template_get(context, cluster_template.id)


def cluster_template_destroy(context, cluster_template_id):
    session = get_session()
    with session.begin():
        cluster_template = _cluster_template_get(context, session,
                                                 cluster_template_id)

        if not cluster_template:
            # raise not found error
            raise RuntimeError("Cluster Template not found!")

        session.delete(cluster_template)


## Node Group Template ops

def _node_group_template_get(context, session, node_group_template_id):
    query = model_query(m.NodeGroupTemplate, context, session)
    return query.filter_by(id=node_group_template_id).first()


def node_group_template_get(context, node_group_template_id):
    return _node_group_template_get(context, get_session(),
                                    node_group_template_id)


def node_group_template_get_all(context):
    query = model_query(m.NodeGroupTemplate, context)
    return query.all()


def node_group_template_create(context, values):
    node_group_template = m.NodeGroupTemplate()
    node_group_template.update(values)

    try:
        node_group_template.save()
    except db_exc.DBDuplicateEntry as e:
        # raise exception about duplicated columns (e.columns)
        raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return node_group_template


def node_group_template_destroy(context, node_group_template_id):
    session = get_session()
    with session.begin():
        node_group_template = _node_group_template_get(context, session,
                                                       node_group_template_id)

        if not node_group_template:
            # raise not found error
            raise RuntimeError("Node Group Template not found!")

        session.delete(node_group_template)


## Data Source ops

def _data_source_get(context, session, data_source_id):
    query = model_query(m.DataSource, context, session)
    return query.filter_by(id=data_source_id).first()


def data_source_get(context, data_source_id):
    return _data_source_get(context, get_session(), data_source_id)


def data_source_get_all(context):
    query = model_query(m.DataSource, context)
    return query.all()


def data_source_create(context, values):
    data_source = m.DataSource()
    data_source.update(values)

    try:
        data_source.save()
    except db_exc.DBDuplicateEntry as e:
        # raise exception about duplicated columns (e.columns)
        raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return data_source


def data_source_destroy(context, data_source_id):
    session = get_session()
    with session.begin():
        data_source = _data_source_get(context, session, data_source_id)

        if not data_source:
            # raise not found error
            raise RuntimeError("Data Source not found!")

        session.delete(data_source)


## Job ops

def _job_get(context, session, job_id):
    query = model_query(m.Job, context, session)
    return query.filter_by(id=job_id).first()


def job_get(context, job_id):
    return _job_get(context, get_session(), job_id)


def job_get_all(context):
    query = model_query(m.Job, context)
    return query.all()


def job_create(context, values):
    job = m.Job()
    job.update(values)

    try:
        job.save()
    except db_exc.DBDuplicateEntry as e:
        # raise exception about duplicated columns (e.columns)
        raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return job


def job_destroy(context, job_id):
    session = get_session()
    with session.begin():
        job = _job_get(context, session, job_id)

        if not job:
            # raise not found error
            raise RuntimeError("Job not found!")

        session.delete(job)


## JobExecution ops

def _job_execution_get(context, job_execution_id):
    query = model_query(m.JobExecution, context, get_session())
    return query.filter_by(id=job_execution_id).first()


def job_execution_get(context, job_execution_id):
    return _job_execution_get(context, job_execution_id)


def job_execution_get_all(context):
    query = model_query(m.JobExecution, context)
    return query.all()


def job_execution_create(context, values):
    session = get_session()

    with session.begin():
        job_ex = m.JobExecution()
        job_ex.update(values)
        try:
            job_ex.save()
        except db_exc.DBDuplicateEntry as e:
            # raise exception about duplicated columns (e.columns)
            raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return job_ex


def job_execution_update(context, job_execution, values):
    session = get_session()

    with session.begin():
        job_ex = _job_execution_get(context, job_execution)
        if not job_ex:
            # raise not found error
            raise RuntimeError("JobExecution not found!")
        job_ex.update(values)
        job_ex.save(session=session)

    return _job_execution_get(context, job_execution)


def job_execution_destroy(context, job_execution_id):
    session = get_session()
    with session.begin():
        job_ex = _job_execution_get(context, job_execution_id)

        if not job_ex:
            # raise not found error
            raise RuntimeError("JobExecution not found!")

        session.delete(job_ex)


## JobOrigin ops

def _job_origin_get(context, session, job_origin_id):
    query = model_query(m.JobOrigin, context, session)
    return query.filter_by(id=job_origin_id).first()


def job_origin_get(context, job_origin_id):
    return _job_origin_get(context, get_session(), job_origin_id)


def job_origin_get_all(context):
    query = model_query(m.JobOrigin, context)
    return query.all()


def job_origin_create(context, values):
    job_origin = m.JobOrigin()
    job_origin.update(values)

    try:
        job_origin.save()
    except db_exc.DBDuplicateEntry as e:
        # raise exception about duplicated columns (e.columns)
        raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return job_origin


def job_origin_update(context, job_origin, values):
    session = get_session()

    with session.begin():
        job_origin = _job_origin_get(context, session, job_origin)
        if not job_origin:
            # raise not found error
            raise RuntimeError("JobOrigin not found!")
        job_origin.update(values)
        job_origin.save()
    return _job_origin_get(context, session, job_origin)


def job_origin_destroy(context, job_origin_id):
    session = get_session()
    with session.begin():
        job_origin = _job_origin_get(context, session, job_origin_id)

        if not job_origin:
            # raise not found error
            raise RuntimeError("JobOrigin not found!")

        session.delete(job_origin)

## JobBinary ops


def job_binary_get_all(context):
    """Returns JobBinary objects that do not contain a data field

    The data column uses deferred loading.
    """
    query = model_query(m.JobBinary, context)
    return query.all()


def job_binary_get(context, job_binary_id):
    """Returns a JobBinary object that does not contain a data field

    The data column uses deferred loadling.
    """
    query = model_query(m.JobBinary, context).filter_by(id=job_binary_id)
    return query.first()


def job_binary_get_raw_data(context, job_binary_id):
    """Returns only the data field for the specified JobBinary."""
    query = model_query(m.JobBinary, context).options(sa.orm.undefer("data"))
    res = query.filter_by(id=job_binary_id).first()
    if res is not None:
        res = res.data
    return res


def job_binary_create(context, values):
    """Returns a JobBinary that does not contain a data field

    The data column uses deferred loading.
    """
    job_binary = m.JobBinary()
    job_binary.update(values)

    try:
        job_binary.save()
    except db_exc.DBDuplicateEntry as e:
        # raise exception about duplicated columns (e.columns)
        raise RuntimeError("DBDuplicateEntry: %s" % e.columns)

    return job_binary_get(context, job_binary.id)


def job_binary_destroy(context, job_binary_id):
    session = get_session()
    with session.begin():

        job_binary = model_query(m.JobBinary,
                                 context).filter_by(id=job_binary_id).first()

        if not job_binary:
            # raise not found error
            raise RuntimeError("JobBinary not found!")

        session.delete(job_binary)
