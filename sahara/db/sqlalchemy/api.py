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
import threading

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log as logging
import six
import sqlalchemy as sa

from sahara.db.sqlalchemy import models as m
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.i18n import _LW


LOG = logging.getLogger(__name__)

CONF = cfg.CONF

_FACADE = None
_LOCK = threading.Lock()


def _create_facade_lazily():
    global _LOCK, _FACADE

    if _FACADE is None:
        with _LOCK:
            if _FACADE is None:
                _FACADE = db_session.EngineFacade.from_config(CONF,
                                                              sqlite_fk=True)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def cleanup():
    global _FACADE
    _FACADE = None


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def model_query(model, context, session=None, project_only=True):
    """Query helper.

    :param model: base model to query
    :param context: context to query under
    :param project_only: if present and context is user-type, then restrict
            query to match the context's tenant_id.
    """
    session = session or get_session()

    query = session.query(model)

    if project_only and not context.is_admin:
        query = query.filter_by(tenant_id=context.tenant_id)

    return query


def count_query(model, context, session=None, project_only=None):
    """Count query helper.

    :param model: base model to query
    :param context: context to query under
    :param project_only: if present and context is user-type, then restrict
            query to match the context's project_id.
    """
    return model_query(sa.func.count(model.id), context, session, project_only)


def in_filter(query, cls, search_opts):
    """Add 'in' filters for specified columns.

    Add a sqlalchemy 'in' filter to the query for any entry in the
    'search_opts' dict where the key is the name of a column in
    'cls' and the value is a tuple.

    This allows the value of a column to be matched
    against multiple possible values (OR).

    Return the modified query and any entries in search_opts
    whose keys do not match columns or whose values are not
    tuples.

    :param query: a non-null query object
    :param cls: the database model class that filters will apply to
    :param search_opts: a dictionary whose key/value entries are interpreted as
    column names and search values
    :returns: a tuple containing the modified query and a dictionary of
    unused search_opts
    """
    if not search_opts:
        return query, search_opts

    remaining = {}
    for k, v in six.iteritems(search_opts):
        if type(v) == tuple and k in cls.__table__.columns:
            col = cls.__table__.columns[k]
            query = query.filter(col.in_(v))
        else:
            remaining[k] = v
    return query, remaining


def like_filter(query, cls, search_opts):
    """Add 'like' filters for specified columns.

    Add a sqlalchemy 'like' filter to the query for any entry in the
    'search_opts' dict where the key is the name of a column in
    'cls' and the value is a string containing '%'.

    This allows the value of a column to be matched
    against simple sql string patterns using LIKE and the
    '%' wildcard.

    Return the modified query and any entries in search_opts
    whose keys do not match columns or whose values are not
    strings containing '%'.

    :param query: a non-null query object
    :param cls: the database model class the filters will apply to
    :param search_opts: a dictionary whose key/value entries are interpreted as
    column names and search patterns
    :returns: a tuple containing the modified query and a dictionary of
    unused search_opts
    """
    if not search_opts:
        return query, search_opts

    remaining = {}
    for k, v in six.iteritems(search_opts):
        if isinstance(v, six.string_types) and (
                '%' in v and k in cls.__table__.columns):
            col = cls.__table__.columns[k]
            query = query.filter(col.like(v))
        else:
            remaining[k] = v
    return query, remaining


def setup_db():
    try:
        engine = get_engine()
        m.Cluster.metadata.create_all(engine)
    except sa.exc.OperationalError as e:
        LOG.warning(_LW("Database registration exception: {exc}")
                    .format(exc=e))
        return False
    return True


def drop_db():
    try:
        engine = get_engine()
        m.Cluster.metadata.drop_all(engine)
    except Exception as e:
        LOG.warning(_LW("Database shutdown exception: {exc}").format(exc=e))
        return False
    return True


# Helpers for building constraints / equality checks


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


# Cluster ops

def _cluster_get(context, session, cluster_id):
    query = model_query(m.Cluster, context, session)
    return query.filter_by(id=cluster_id).first()


def cluster_get(context, cluster_id):
    return _cluster_get(context, get_session(), cluster_id)


def cluster_get_all(context, **kwargs):
    query = model_query(m.Cluster, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def cluster_create(context, values):
    values = values.copy()
    cluster = m.Cluster()
    node_groups = values.pop("node_groups", [])
    cluster.update(values)

    session = get_session()
    with session.begin():
        try:
            cluster.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for Cluster: %s") % e.columns)

        try:
            for ng in node_groups:
                node_group = m.NodeGroup()
                node_group.update({"cluster_id": cluster.id})
                node_group.update(ng)
                node_group.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for NodeGroup: %s") % e.columns)

    return cluster_get(context, cluster.id)


def cluster_update(context, cluster_id, values):
    session = get_session()

    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)
        if cluster is None:
            raise ex.NotFoundException(cluster_id,
                                       _("Cluster id '%s' not found!"))
        cluster.update(values)

    return cluster


def cluster_destroy(context, cluster_id):
    session = get_session()
    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)
        if not cluster:
            raise ex.NotFoundException(cluster_id,
                                       _("Cluster id '%s' not found!"))

        session.delete(cluster)


# Node Group ops

def _node_group_get(context, session, node_group_id):
    query = model_query(m.NodeGroup, context, session)
    return query.filter_by(id=node_group_id).first()


def node_group_add(context, cluster_id, values):
    session = get_session()

    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)
        if not cluster:
            raise ex.NotFoundException(cluster_id,
                                       _("Cluster id '%s' not found!"))

        node_group = m.NodeGroup()
        node_group.update({"cluster_id": cluster_id})
        node_group.update(values)
        session.add(node_group)

    return node_group.id


def node_group_update(context, node_group_id, values):
    session = get_session()
    with session.begin():
        node_group = _node_group_get(context, session, node_group_id)
        if not node_group:
            raise ex.NotFoundException(node_group_id,
                                       _("Node Group id '%s' not found!"))

        node_group.update(values)


def node_group_remove(context, node_group_id):
    session = get_session()

    with session.begin():
        node_group = _node_group_get(context, session, node_group_id)
        if not node_group:
            raise ex.NotFoundException(node_group_id,
                                       _("Node Group id '%s' not found!"))

        session.delete(node_group)


# Instance ops

def _instance_get(context, session, instance_id):
    query = model_query(m.Instance, context, session)
    return query.filter_by(id=instance_id).first()


def instance_add(context, node_group_id, values):
    session = get_session()

    with session.begin():
        node_group = _node_group_get(context, session, node_group_id)
        if not node_group:
            raise ex.NotFoundException(node_group_id,
                                       _("Node Group id '%s' not found!"))

        instance = m.Instance()
        instance.update({"node_group_id": node_group_id})
        instance.update(values)
        session.add(instance)

        node_group = _node_group_get(context, session, node_group_id)
        node_group.count += 1

    return instance.id


def instance_update(context, instance_id, values):
    session = get_session()
    with session.begin():
        instance = _instance_get(context, session, instance_id)
        if not instance:
            raise ex.NotFoundException(instance_id,
                                       _("Instance id '%s' not found!"))

        instance.update(values)


def instance_remove(context, instance_id):
    session = get_session()
    with session.begin():
        instance = _instance_get(context, session, instance_id)
        if not instance:
            raise ex.NotFoundException(instance_id,
                                       _("Instance id '%s' not found!"))

        session.delete(instance)

        node_group_id = instance.node_group_id
        node_group = _node_group_get(context, session, node_group_id)
        node_group.count -= 1


# Volumes ops

def append_volume(context, instance_id, volume_id):
    session = get_session()
    with session.begin():
        instance = _instance_get(context, session, instance_id)
        if not instance:
            raise ex.NotFoundException(instance_id,
                                       _("Instance id '%s' not found!"))

        instance.volumes.append(volume_id)


def remove_volume(context, instance_id, volume_id):
    session = get_session()
    with session.begin():
        instance = _instance_get(context, session, instance_id)
        if not instance:
            raise ex.NotFoundException(instance_id,
                                       _("Instance id '%s' not found!"))

        instance.volumes.remove(volume_id)


# Cluster Template ops

def _cluster_template_get(context, session, cluster_template_id):
    query = model_query(m.ClusterTemplate, context, session)
    return query.filter_by(id=cluster_template_id).first()


def cluster_template_get(context, cluster_template_id):
    return _cluster_template_get(context, get_session(), cluster_template_id)


def cluster_template_get_all(context, **kwargs):
    query = model_query(m.ClusterTemplate, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def cluster_template_create(context, values):
    values = values.copy()
    cluster_template = m.ClusterTemplate()
    node_groups = values.pop("node_groups") or []
    cluster_template.update(values)

    session = get_session()
    with session.begin():
        try:
            cluster_template.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for ClusterTemplate: %s") % e.columns)

        try:
            for ng in node_groups:
                node_group = m.TemplatesRelation()
                node_group.update({"cluster_template_id": cluster_template.id})
                node_group.update(ng)
                node_group.save(session=session)

        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for TemplatesRelation: %s") % e.columns)

    return cluster_template_get(context, cluster_template.id)


def cluster_template_destroy(context, cluster_template_id,
                             ignore_default=False):
    session = get_session()
    with session.begin():
        cluster_template = _cluster_template_get(context, session,
                                                 cluster_template_id)
        if not cluster_template:
            raise ex.NotFoundException(
                cluster_template_id,
                _("Cluster Template id '%s' not found!"))
        elif not ignore_default and cluster_template.is_default:
            raise ex.DeletionFailed(
                _("Cluster template id '%s' "
                  "is a default template") % cluster_template.id)

        session.delete(cluster_template)


def cluster_template_update(context, values, ignore_default=False):
    node_groups = values.pop("node_groups", [])

    session = get_session()
    with session.begin():
        cluster_template_id = values['id']
        cluster_template = (_cluster_template_get(
            context, session, cluster_template_id))
        if not cluster_template:
            raise ex.NotFoundException(
                cluster_template_id,
                _("Cluster Template id '%s' not found!"))

        elif not ignore_default and cluster_template.is_default:
            raise ex.UpdateFailedException(
                cluster_template_id,
                _("ClusterTemplate id '%s' can not be updated. "
                  "It is a default template.")
            )

        name = values.get('name')
        if name:
            same_name_tmpls = model_query(
                m.ClusterTemplate, context).filter_by(
                name=name).all()
            if (len(same_name_tmpls) > 0 and
                    same_name_tmpls[0].id != cluster_template_id):
                raise ex.DBDuplicateEntry(
                    _("Cluster Template can not be updated. "
                      "Another cluster template with name %s already exists.")
                    % name
                )

        if len(cluster_template.clusters) > 0:
            raise ex.UpdateFailedException(
                cluster_template_id,
                _("Cluster Template id '%s' can not be updated. "
                  "It is referenced by at least one cluster.")
            )
        cluster_template.update(values)

        model_query(m.TemplatesRelation, context).filter_by(
            cluster_template_id=cluster_template_id).delete()
        for ng in node_groups:
            node_group = m.TemplatesRelation()
            node_group.update(ng)
            node_group.update({"cluster_template_id": cluster_template_id})
            node_group.save(session=session)

    return cluster_template


# Node Group Template ops

def _node_group_template_get(context, session, node_group_template_id):
    query = model_query(m.NodeGroupTemplate, context, session)
    return query.filter_by(id=node_group_template_id).first()


def node_group_template_get(context, node_group_template_id):
    return _node_group_template_get(context, get_session(),
                                    node_group_template_id)


def node_group_template_get_all(context, **kwargs):
    query = model_query(m.NodeGroupTemplate, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def node_group_template_create(context, values):
    node_group_template = m.NodeGroupTemplate()
    node_group_template.update(values)

    session = get_session()
    with session.begin():
        try:
            node_group_template.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for NodeGroupTemplate: %s") % e.columns)

    return node_group_template


def node_group_template_destroy(context, node_group_template_id,
                                ignore_default=False):
    session = get_session()
    with session.begin():
        node_group_template = _node_group_template_get(context, session,
                                                       node_group_template_id)
        if not node_group_template:
            raise ex.NotFoundException(
                node_group_template_id,
                _("Node Group Template id '%s' not found!"))
        elif not ignore_default and node_group_template.is_default:
            raise ex.DeletionFailed(
                _("Node group template id '%s' "
                  "is a default template") % node_group_template_id)

        session.delete(node_group_template)


def node_group_template_update(context, values, ignore_default=False):
    session = get_session()
    with session.begin():
        ngt_id = values['id']
        node_group_template = (
            _node_group_template_get(context, session, ngt_id))
        if not node_group_template:
            raise ex.NotFoundException(
                ngt_id, _("NodeGroupTemplate id '%s' not found"))
        elif not ignore_default and node_group_template.is_default:
            raise ex.UpdateFailedException(
                ngt_id,
                _("NodeGroupTemplate id '%s' can not be updated. "
                  "It is a default template.")
            )

        name = values.get('name')
        if name and name != node_group_template.name:
            same_name_tmpls = model_query(
                m.NodeGroupTemplate, context).filter_by(name=name).all()
            if (len(same_name_tmpls) > 0 and
                    same_name_tmpls[0].id != ngt_id):
                raise ex.DBDuplicateEntry(
                    _("Node Group Template can not be updated. "
                      "Another node group template with name %s "
                      "already exists.")
                    % name
                )

        # Check to see that the node group template to be updated is not in
        # use by an existing cluster.
        for template_relationship in node_group_template.templates_relations:
            if len(template_relationship.cluster_template.clusters) > 0:
                raise ex.UpdateFailedException(
                    ngt_id,
                    _("NodeGroupTemplate id '%s' can not be updated. "
                      "It is referenced by an existing cluster.")
                )

        node_group_template.update(values)
    return node_group_template


# Data Source ops

def _data_source_get(context, session, data_source_id):
    query = model_query(m.DataSource, context, session)
    return query.filter_by(id=data_source_id).first()


def data_source_get(context, data_source_id):
    return _data_source_get(context, get_session(), data_source_id)


def data_source_count(context, **kwargs):
    """Count DataSource objects filtered by search criteria in kwargs.

    Entries in kwargs indicate column names and search values.

    'in' filters will be used to search for any entries in kwargs
    that name DataSource columns and have values of type tuple. This
    allows column values to match multiple values (OR)

    'like' filters will be used for any entries in kwargs that
    name DataSource columns and have string values containing '%'.
    This allows column values to match simple wildcards.

    Any other entries in kwargs will be searched for using filter_by()
    """
    query = model_query(m.DataSource, context)
    query, kwargs = in_filter(query, m.DataSource, kwargs)
    query, kwargs = like_filter(query, m.DataSource, kwargs)

    # Use normal filter_by for remaining keys
    try:
        return query.filter_by(**kwargs).count()
    except Exception as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def data_source_get_all(context, **kwargs):
    query = model_query(m.DataSource, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def data_source_create(context, values):
    data_source = m.DataSource()
    data_source.update(values)

    session = get_session()
    with session.begin():
        try:
            data_source.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for DataSource: %s") % e.columns)

    return data_source


def data_source_destroy(context, data_source_id):
    session = get_session()
    try:
        with session.begin():
            data_source = _data_source_get(context, session, data_source_id)
            if not data_source:
                raise ex.NotFoundException(
                    data_source_id,
                    _("Data Source id '%s' not found!"))
            session.delete(data_source)
    except db_exc.DBError as e:
        msg = ("foreign key constraint" in six.text_type(e) and
               _(" on foreign key constraint") or "")
        raise ex.DeletionFailed(_("Data Source deletion failed%s") % msg)

# JobExecution ops


def _job_execution_get(context, session, job_execution_id):
    query = model_query(m.JobExecution, context, session)
    return query.filter_by(id=job_execution_id).first()


def job_execution_get(context, job_execution_id):
    return _job_execution_get(context, get_session(), job_execution_id)


def job_execution_get_all(context, **kwargs):
    """Get all JobExecutions filtered by **kwargs.

    kwargs key values may be the names of fields in a JobExecution
    plus the following special values with the indicated meaning:

    'cluster.name' -- name of the Cluster referenced by the JobExecution
    'job.name' -- name of the Job referenced by the JobExecution
    'status' -- JobExecution['info']['status']

    e.g. job_execution_get_all(cluster_id=12, input_id=123)
         job_execution_get_all(**{'cluster.name': 'test',
                                  'job.name': 'wordcount'})
    """
    query = model_query(m.JobExecution, context)

    # Remove the external fields if present, they'll
    # be handled with a join and filter
    externals = {k: kwargs.pop(k) for k in ['cluster.name',
                                            'job.name',
                                            'status'] if k in kwargs}

    # Filter JobExecution by the remaining kwargs. This has to be done
    # before application of the joins and filters because those
    # change the class that query.filter_by will apply to
    try:
        query = query.filter_by(**kwargs)
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e

    # Now add the joins and filters for the externals
    if 'cluster.name' in externals:
        query = query.join(m.Cluster).filter(
            m.Cluster.name == externals['cluster.name'])

    if 'job.name' in externals:
        query = query.join(m.Job).filter(
            m.Job.name == externals['job.name'])

    res = query.all()

    # 'info' is a JsonDictType which is stored as a string.
    # It would be possible to search for the substring containing
    # the value of 'status' in 'info', but 'info' also contains
    # data returned from a client and not managed by Sahara.
    # In the case of Oozie jobs, for example, other fields (actions)
    # also contain 'status'. Therefore we can't filter on it reliably
    # by a substring search in the query.
    if 'status' in externals:
        status = externals['status'].lower()
        res = [je for je in res if (
            je['info'] and je['info'].get('status', '').lower() == status)]
    return res


def job_execution_count(context, **kwargs):
    query = count_query(m.JobExecution, context)
    return query.filter_by(**kwargs).first()[0]


def job_execution_create(context, values):
    session = get_session()

    with session.begin():
        job_ex = m.JobExecution()
        job_ex.update(values)
        try:
            job_ex.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for JobExecution: %s") % e.columns)

    return job_ex


def job_execution_update(context, job_execution_id, values):
    session = get_session()

    with session.begin():
        job_ex = _job_execution_get(context, session, job_execution_id)
        if not job_ex:
            raise ex.NotFoundException(job_execution_id,
                                       _("JobExecution id '%s' not found!"))
        job_ex.update(values)

    return job_ex


def job_execution_destroy(context, job_execution_id):
    session = get_session()
    with session.begin():
        job_ex = _job_execution_get(context, session, job_execution_id)
        if not job_ex:
            raise ex.NotFoundException(job_execution_id,
                                       _("JobExecution id '%s' not found!"))

        session.delete(job_ex)


# Job ops

def _job_get(context, session, job_id):
    query = model_query(m.Job, context, session)
    return query.filter_by(id=job_id).first()


def job_get(context, job_id):
    return _job_get(context, get_session(), job_id)


def job_get_all(context, **kwargs):
    query = model_query(m.Job, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def _append_job_binaries(context, session, from_list, to_list):
    for job_binary_id in from_list:
        job_binary = model_query(
            m.JobBinary, context, session).filter_by(id=job_binary_id).first()
        if job_binary is not None:
            to_list.append(job_binary)


def job_create(context, values):
    mains = values.pop("mains", [])
    libs = values.pop("libs", [])

    session = get_session()
    with session.begin():
        job = m.Job()
        job.update(values)
        # libs and mains are 'lazy' objects. The initialization below
        # is needed here because it provides libs and mains to be initialized
        # within a session even if the lists are empty
        job.mains = []
        job.libs = []
        try:
            _append_job_binaries(context, session, mains, job.mains)
            _append_job_binaries(context, session, libs, job.libs)

            job.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for Job: %s") % e.columns)

    return job


def job_update(context, job_id, values):
    session = get_session()

    with session.begin():
        job = _job_get(context, session, job_id)
        if not job:
            raise ex.NotFoundException(job_id,
                                       _("Job id '%s' not found!"))
        job.update(values)

    return job


def job_destroy(context, job_id):
    session = get_session()
    try:
        with session.begin():
            job = _job_get(context, session, job_id)
            if not job:
                raise ex.NotFoundException(job_id,
                                           _("Job id '%s' not found!"))
            session.delete(job)
    except db_exc.DBError as e:
        msg = ("foreign key constraint" in six.text_type(e) and
               _(" on foreign key constraint") or "")
        raise ex.DeletionFailed(_("Job deletion failed%s") % msg)


# JobBinary ops

def _job_binary_get(context, session, job_binary_id):
    query = model_query(m.JobBinary, context, session)
    return query.filter_by(id=job_binary_id).first()


def job_binary_get_all(context, **kwargs):
    """Returns JobBinary objects that do not contain a data field

    The data column uses deferred loading.
    """
    query = model_query(m.JobBinary, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def job_binary_get(context, job_binary_id):
    """Returns a JobBinary object that does not contain a data field

    The data column uses deferred loadling.
    """
    return _job_binary_get(context, get_session(), job_binary_id)


def job_binary_create(context, values):
    """Returns a JobBinary that does not contain a data field

    The data column uses deferred loading.
    """
    job_binary = m.JobBinary()
    job_binary.update(values)

    session = get_session()
    with session.begin():
        try:
            job_binary.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for JobBinary: %s") % e.columns)

    return job_binary


def _check_job_binary_referenced(ctx, session, job_binary_id):
    args = {"JobBinary_id": job_binary_id}
    mains = model_query(m.mains_association, ctx, session,
                        project_only=False).filter_by(**args)
    libs = model_query(m.libs_association, ctx, session,
                       project_only=False).filter_by(**args)

    return mains.first() is not None or libs.first() is not None


def job_binary_destroy(context, job_binary_id):
    session = get_session()
    with session.begin():
        job_binary = _job_binary_get(context, session, job_binary_id)
        if not job_binary:
            raise ex.NotFoundException(job_binary_id,
                                       _("JobBinary id '%s' not found!"))

        if _check_job_binary_referenced(context, session, job_binary_id):
            raise ex.DeletionFailed(
                _("JobBinary is referenced and cannot be deleted"))

        session.delete(job_binary)


# JobBinaryInternal ops

def _job_binary_internal_get(context, session, job_binary_internal_id):
    query = model_query(m.JobBinaryInternal, context, session)
    return query.filter_by(id=job_binary_internal_id).first()


def job_binary_internal_get_all(context, **kwargs):
    """Returns JobBinaryInternal objects that do not contain a data field

    The data column uses deferred loading.
    """
    query = model_query(m.JobBinaryInternal, context)
    try:
        return query.filter_by(**kwargs).all()
    except sa.exc.InvalidRequestError as e:
        if kwargs:
            # If kwargs is non-empty then we assume this
            # is a bad field reference. User asked for something
            # that doesn't exist, so return empty list
            return []
        raise e


def job_binary_internal_get(context, job_binary_internal_id):
    """Returns a JobBinaryInternal object that does not contain a data field

    The data column uses deferred loadling.
    """
    return _job_binary_internal_get(context, get_session(),
                                    job_binary_internal_id)


def job_binary_internal_get_raw_data(context, job_binary_internal_id):
    """Returns only the data field for the specified JobBinaryInternal."""
    query = model_query(m.JobBinaryInternal, context)
    res = query.filter_by(id=job_binary_internal_id).first()

    if res is not None:
        datasize_KB = res.datasize / 1024.0
        if datasize_KB > CONF.job_binary_max_KB:
            raise ex.DataTooBigException(
                round(datasize_KB, 1), CONF.job_binary_max_KB,
                _("Size of internal binary (%(size)sKB) is greater than the "
                  "maximum (%(maximum)sKB)"))

        # This assignment is sufficient to load the deferred column
        res = res.data
    return res


def job_binary_internal_create(context, values):
    """Returns a JobBinaryInternal that does not contain a data field

    The data column uses deferred loading.
    """
    values["datasize"] = len(values["data"])
    datasize_KB = values["datasize"] / 1024.0
    if datasize_KB > CONF.job_binary_max_KB:
        raise ex.DataTooBigException(
            round(datasize_KB, 1), CONF.job_binary_max_KB,
            _("Size of internal binary (%(size)sKB) is greater "
              "than the maximum (%(maximum)sKB)"))

    job_binary_int = m.JobBinaryInternal()
    job_binary_int.update(values)

    session = get_session()
    with session.begin():
        try:
            job_binary_int.save(session=session)
        except db_exc.DBDuplicateEntry as e:
            raise ex.DBDuplicateEntry(
                _("Duplicate entry for JobBinaryInternal: %s") % e.columns)

    return job_binary_internal_get(context, job_binary_int.id)


def job_binary_internal_destroy(context, job_binary_internal_id):
    session = get_session()
    with session.begin():
        job_binary_internal = _job_binary_internal_get(context, session,
                                                       job_binary_internal_id)
        if not job_binary_internal:
            raise ex.NotFoundException(
                job_binary_internal_id,
                _("JobBinaryInternal id '%s' not found!"))

        session.delete(job_binary_internal)

# Events ops


def _cluster_provision_step_get(context, session, provision_step_id):
    query = model_query(m.ClusterProvisionStep, context, session)
    return query.filter_by(id=provision_step_id).first()


def _cluster_provision_step_update(context, session, step_id):
    step = _cluster_provision_step_get(context, session, step_id)

    if step is None:
        raise ex.NotFoundException(
            step_id,
            _("Cluster Provision Step id '%s' not found!"))

    if step.successful is not None:
        return
    if len(step.events) == step.total:
        for event in step.events:
            session.delete(event)
        step.update({'successful': True})


def cluster_provision_step_add(context, cluster_id, values):
    session = get_session()

    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)
        if not cluster:
            raise ex.NotFoundException(cluster_id,
                                       _("Cluster id '%s' not found!"))

        provision_step = m.ClusterProvisionStep()
        values['cluster_id'] = cluster_id
        values['tenant_id'] = context.tenant_id
        provision_step.update(values)
        session.add(provision_step)

    return provision_step.id


def cluster_provision_step_update(context, step_id):
    if CONF.disable_event_log:
        return
    session = get_session()
    with session.begin():
        _cluster_provision_step_update(context, session, step_id)


def cluster_provision_progress_update(context, cluster_id):
    if CONF.disable_event_log:
        return _cluster_get(context, get_session(), cluster_id)
    session = get_session()
    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)

        if cluster is None:
            raise ex.NotFoundException(cluster_id,
                                       _("Cluster id '%s' not found!"))
        for step in cluster.provision_progress:
            if step.successful is None:
                _cluster_provision_step_update(context, session, step.id)
        result_cluster = _cluster_get(context, session, cluster_id)
    return result_cluster


def cluster_event_add(context, step_id, values):
    session = get_session()

    with session.begin():
        provision_step = _cluster_provision_step_get(
            context, session, step_id)

        if not provision_step:
            raise ex.NotFoundException(
                step_id,
                _("Cluster Provision Step id '%s' not found!"))

        event = m.ClusterEvent()
        values['step_id'] = step_id
        if not values['successful']:
            provision_step.update({'successful': False})
        event.update(values)
        session.add(event)

    return event.id
