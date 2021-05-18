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

import copy
import sys
import threading

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils
from oslo_log import log as logging
import six
import sqlalchemy as sa

from sahara.db.sqlalchemy import models as m
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.validations import acl as validate
from sahara.utils import types


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


def _parse_sorting_args(sort_by):
    if sort_by is None:
        sort_by = "id"
    if sort_by[0] == "-":
        return sort_by[1:], "desc"
    return sort_by, "asc"


def _get_prev_and_next_objects(objects, limit, marker, order=None):
    if order == 'desc':
        objects.reverse()
    position = None
    if limit is None:
        return None, None
    if marker:
        for pos, obj in enumerate(objects):
            if obj.id == marker.id:
                position = pos
                break
        else:
            return None, None
        if position - limit >= 0:
            prev_marker = objects[position - limit].id
        else:
            prev_marker = None
        if position + limit < len(objects):
            next_marker = objects[position + limit].id
        else:
            next_marker = None
    else:
        if limit < len(objects):
            next_marker = objects[limit - 1].id
        else:
            next_marker = None
        prev_marker = None
    return prev_marker, next_marker


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
        query = query.filter(
            (model.tenant_id == context.tenant_id) |
            getattr(model, 'is_public', False))

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


def _get_regex_op(connection):
    db = connection.split(':')[0].split('+')[0]
    regexp_op_map = {
        'postgresql': '~',
        'mysql': 'REGEXP'
    }
    return regexp_op_map.get(db, None)


def regex_filter(query, cls, regex_cols, search_opts):
    """Add regex filters for specified columns.

    Add a regex filter to the query for any entry in the
    'search_opts' dict where the key is the name of a column in
    'cls' and listed in 'regex_cols' and the value is a string.

    Return the modified query and any entries in search_opts
    whose keys do not match columns or whose values are not
    strings.

    This is only supported for mysql and postgres. For other
    databases, the query is not altered.

    :param query: a non-null query object
    :param cls: the database model class the filters will apply to
    :param regex_cols: a list of columns for which regex is supported
    :param search_opts: a dictionary whose key/value entries are interpreted as
    column names and search patterns
    :returns: a tuple containing the modified query and a dictionary of
    unused search_opts
    """

    regex_op = _get_regex_op(CONF.database.connection)
    if not regex_op:
        return query, copy.copy(search_opts)

    remaining = {}
    for k, v in six.iteritems(search_opts):
        if isinstance(v, six.string_types) and (
                k in cls.__table__.columns and k in regex_cols):
            col = cls.__table__.columns[k]
            query = query.filter(col.op(regex_op)(v))
        else:
            remaining[k] = v
    return query, remaining


def setup_db():
    try:
        engine = get_engine()
        m.Cluster.metadata.create_all(engine)
    except sa.exc.OperationalError as e:
        LOG.warning("Database registration exception: {exc}".format(exc=e))
        return False
    return True


def drop_db():
    try:
        engine = get_engine()
        m.Cluster.metadata.drop_all(engine)
    except Exception as e:
        LOG.warning("Database shutdown exception: {exc}".format(exc=e))
        return False
    return True


# Cluster ops

def _cluster_get(context, session, cluster_id):
    query = model_query(m.Cluster, context, session)
    return query.filter_by(id=cluster_id).first()


def cluster_get(context, cluster_id):
    return _cluster_get(context, get_session(), cluster_id)


def cluster_get_all(context, regex_search=False,
                    limit=None, marker=None, sort_by=None, **kwargs):

    sort_by, order = _parse_sorting_args(sort_by)
    regex_cols = ['name', 'description', 'plugin_name', 'tenant_id']

    query = model_query(m.Cluster, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.Cluster, regex_cols, kwargs)

    limit = int(limit) if limit else None
    marker = cluster_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(query.filter_by(**kwargs), m.Cluster,
                                  limit, [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def cluster_create(context, values):
    values = values.copy()
    cluster = m.Cluster()
    node_groups = values.pop("node_groups", [])
    cluster.update(values)

    session = get_session()
    try:
        with session.begin():
            session.add(cluster)
            session.flush(objects=[cluster])

            for ng in node_groups:
                node_group = m.NodeGroup()
                node_group.update(ng)
                node_group.update({"cluster_id": cluster.id})
                session.add(node_group)

    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for object %(object)s. Failed on columns: "
              "%(columns)s") % {"object": e.value, "columns": e.columns})

    return cluster_get(context, cluster.id)


def cluster_update(context, cluster_id, values):
    session = get_session()

    try:
        with session.begin():
            cluster = _cluster_get(context, session, cluster_id)
            if cluster is None:
                raise ex.NotFoundException(cluster_id,
                                           _("Cluster id '%s' not found!"))
            cluster.update(values)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for Cluster: %s") % e.columns)

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


def cluster_template_get_all(context, regex_search=False,
                             marker=None, limit=None, sort_by=None, **kwargs):

    regex_cols = ['name', 'description', 'plugin_name', 'tenant_id']
    sort_by, order = _parse_sorting_args(sort_by)
    query = model_query(m.ClusterTemplate, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.ClusterTemplate, regex_cols, kwargs)

    limit = int(limit) if limit else None

    marker = cluster_template_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(query.filter_by(**kwargs),
                                  m.ClusterTemplate,
                                  limit, [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def cluster_template_create(context, values):
    values = values.copy()
    cluster_template = m.ClusterTemplate()
    node_groups = values.pop("node_groups") or []
    cluster_template.update(values)

    session = get_session()
    try:
        with session.begin():
            session.add(cluster_template)
            session.flush(objects=[cluster_template])

            for ng in node_groups:
                node_group = m.TemplatesRelation()
                node_group.update({"cluster_template_id": cluster_template.id})
                node_group.update(ng)
                session.add(node_group)

    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for object %(object)s. Failed on columns: "
              "%(columns)s") % {"object": e.value, "columns": e.columns})

    return cluster_template_get(context, cluster_template.id)


def cluster_template_destroy(context, cluster_template_id,
                             ignore_prot_on_def=False):
    session = get_session()
    with session.begin():
        cluster_template = _cluster_template_get(context, session,
                                                 cluster_template_id)
        if not cluster_template:
            raise ex.NotFoundException(
                cluster_template_id,
                _("Cluster Template id '%s' not found!"))

        validate.check_tenant_for_delete(context, cluster_template)
        if not (cluster_template.is_default and ignore_prot_on_def):
            validate.check_protected_from_delete(cluster_template)

        session.delete(cluster_template)


def cluster_template_update(context, values, ignore_prot_on_def=False):
    explicit_node_groups = "node_groups" in values
    if explicit_node_groups:
        node_groups = values.pop("node_groups")
        if node_groups is None:
            node_groups = []

    session = get_session()
    cluster_template_id = values['id']
    try:
        with session.begin():
            cluster_template = (_cluster_template_get(
                context, session, cluster_template_id))
            if not cluster_template:
                raise ex.NotFoundException(
                    cluster_template_id,
                    _("Cluster Template id '%s' not found!"))

            validate.check_tenant_for_update(context, cluster_template)
            if not (cluster_template.is_default and ignore_prot_on_def):
                validate.check_protected_from_update(cluster_template, values)

            if len(cluster_template.clusters) > 0:
                raise ex.UpdateFailedException(
                    cluster_template_id,
                    _("Cluster Template id '%s' can not be updated. "
                      "It is referenced by at least one cluster.")
                )
            cluster_template.update(values)
            # The flush here will cause a duplicate entry exception if
            # unique constraints are violated, before we go ahead and delete
            # the node group templates
            session.flush(objects=[cluster_template])

            # If node_groups has not been specified, then we are
            # keeping the old ones so don't delete!
            if explicit_node_groups:
                model_query(m.TemplatesRelation,
                            context, session=session).filter_by(
                    cluster_template_id=cluster_template_id).delete()

                for ng in node_groups:
                    node_group = m.TemplatesRelation()
                    node_group.update(ng)
                    node_group.update({"cluster_template_id":
                                       cluster_template_id})
                    session.add(node_group)

    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for ClusterTemplate: %s") % e.columns)

    return cluster_template_get(context, cluster_template_id)


# Node Group Template ops

def _node_group_template_get(context, session, node_group_template_id):
    query = model_query(m.NodeGroupTemplate, context, session)
    return query.filter_by(id=node_group_template_id).first()


def node_group_template_get(context, node_group_template_id):
    return _node_group_template_get(context, get_session(),
                                    node_group_template_id)


def node_group_template_get_all(context, regex_search=False, marker=None,
                                limit=None, sort_by=None, **kwargs):
    sort_by, order = _parse_sorting_args(sort_by)
    regex_cols = ['name', 'description', 'plugin_name', 'tenant_id']
    limit = int(limit) if limit else None
    query = model_query(m.NodeGroupTemplate, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.NodeGroupTemplate, regex_cols, kwargs)

    marker = node_group_template_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(
        query.filter_by(**kwargs), m.NodeGroupTemplate,
        limit, [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def node_group_template_create(context, values):
    node_group_template = m.NodeGroupTemplate()
    node_group_template.update(values)

    session = get_session()
    try:
        with session.begin():
            session.add(node_group_template)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for NodeGroupTemplate: %s") % e.columns)

    return node_group_template


def node_group_template_destroy(context, node_group_template_id,
                                ignore_prot_on_def=False):
    session = get_session()
    with session.begin():
        node_group_template = _node_group_template_get(context, session,
                                                       node_group_template_id)
        if not node_group_template:
            raise ex.NotFoundException(
                node_group_template_id,
                _("Node Group Template id '%s' not found!"))

        validate.check_tenant_for_delete(context, node_group_template)
        if not (node_group_template.is_default and ignore_prot_on_def):
            validate.check_protected_from_delete(node_group_template)

        session.delete(node_group_template)


def node_group_template_update(context, values, ignore_prot_on_def=False):
    session = get_session()
    try:
        with session.begin():
            ngt_id = values['id']
            ngt = _node_group_template_get(context, session, ngt_id)
            if not ngt:
                raise ex.NotFoundException(
                    ngt_id, _("NodeGroupTemplate id '%s' not found"))

            validate.check_tenant_for_update(context, ngt)
            if not (ngt.is_default and ignore_prot_on_def):
                validate.check_protected_from_update(ngt, values)

            # Check to see that the node group template to be updated is not in
            # use by an existing cluster.
            for template_relationship in ngt.templates_relations:
                if len(template_relationship.cluster_template.clusters) > 0:
                    raise ex.UpdateFailedException(
                        ngt_id,
                        _("NodeGroupTemplate id '%s' can not be updated. "
                          "It is referenced by an existing cluster.")
                    )

            ngt.update(values)

            # Here we update any cluster templates that reference the
            # updated node group template
            for template_relationship in ngt.templates_relations:
                ct_id = template_relationship.cluster_template_id
                ct = cluster_template_get(
                    context, template_relationship.cluster_template_id)
                node_groups = ct.node_groups
                ct_node_groups = []
                for ng in node_groups:
                    # Need to fill in all node groups, not just
                    # the modified group
                    ng_to_add = ng
                    if ng.node_group_template_id == ngt_id:
                        # use the updated node group template
                        ng_to_add = ngt
                    ng_to_add = ng_to_add.to_dict()
                    ng_to_add.update(
                        {"count": ng["count"],
                         "node_group_template_id": ng.node_group_template_id})
                    ng_to_add.pop("updated_at", None)
                    ng_to_add.pop("created_at", None)
                    ng_to_add.pop("id", None)
                    ct_node_groups.append(ng_to_add)
                ct_update = {"id": ct_id,
                             "node_groups": ct_node_groups}
                cluster_template_update(context, ct_update, ignore_prot_on_def)

    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for NodeGroupTemplate: %s") % e.columns)

    return ngt


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
    return query.filter_by(**kwargs).count()


def data_source_get_all(context, regex_search=False,
                        limit=None, marker=None, sort_by=None, **kwargs):

    regex_cols = ['name', 'description', 'url']

    sort_by, order = _parse_sorting_args(sort_by)

    query = model_query(m.DataSource, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.DataSource, regex_cols, kwargs)

    limit = int(limit) if limit else None
    marker = data_source_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(query.filter_by(**kwargs), m.DataSource,
                                  limit, [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def data_source_create(context, values):
    data_source = m.DataSource()
    data_source.update(values)

    session = get_session()
    try:
        with session.begin():
            session.add(data_source)
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

            validate.check_tenant_for_delete(context, data_source)
            validate.check_protected_from_delete(data_source)

            session.delete(data_source)
    except db_exc.DBError as e:
        msg = ("foreign key constraint" in six.text_type(e) and
               _(" on foreign key constraint") or "")
        raise ex.DeletionFailed(_("Data Source deletion failed%s") % msg)


def data_source_update(context, values):
    session = get_session()
    try:
        with session.begin():
            ds_id = values['id']
            data_source = _data_source_get(context, session, ds_id)
            if not data_source:
                raise ex.NotFoundException(
                    ds_id, _("DataSource id '%s' not found"))

            validate.check_tenant_for_update(context, data_source)
            validate.check_protected_from_update(data_source, values)

            data_source.update(values)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for DataSource: %s") % e.columns)

    return data_source


# JobExecution ops

def _job_execution_get(context, session, job_execution_id):
    query = model_query(m.JobExecution, context, session)
    return query.filter_by(id=job_execution_id).first()


def job_execution_get(context, job_execution_id):
    return _job_execution_get(context, get_session(), job_execution_id)


def job_execution_get_all(context, regex_search=False,
                          limit=None, marker=None, sort_by=None, **kwargs):
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

    sort_by, order = _parse_sorting_args(sort_by)

    regex_cols = ['job.name', 'cluster.name']

    # Remove the external fields if present, they'll
    # be handled with a join and filter
    externals = {k: kwargs.pop(k) for k in ['cluster.name',
                                            'job.name',
                                            'status'] if k in kwargs}

    # At this time, none of the fields in m.JobExecution itself
    # are candidates for regex search, however this code fragment
    # should remain in case that changes. This is the correct place
    # to insert regex filters on the m.JobExecution class
    query = model_query(m.JobExecution, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.JobExecution, regex_cols, kwargs)

    # Filter JobExecution by the remaining kwargs. This has to be done
    # before application of the joins and filters because those
    # change the class that query.filter_by will apply to
    query = query.filter_by(**kwargs)

    # Now add the joins and filters for the externals
    if 'cluster.name' in externals:
        search_opts = {'name': externals['cluster.name']}
        query = query.join(m.Cluster)
        if regex_filter and 'cluster.name' in regex_cols:
            query, search_opts = regex_filter(query,
                                              m.Cluster, ['name'], search_opts)
        query = query.filter_by(**search_opts)

    if 'job.name' in externals:
        search_opts = {'name': externals['job.name']}
        query = query.join(m.Job)
        if regex_filter and 'job.name' in regex_cols:
            query, search_opts = regex_filter(query,
                                              m.Job, ['name'], search_opts)
        query = query.filter_by(**search_opts)

    res = query.order_by(sort_by).all()

    if order == 'desc':
        res.reverse()

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

    res_page = res
    if marker:
        n = None
        for i, je in enumerate(res):
            if je['id'] == marker:
                n = i
        if n:
            res_page = res[n:]
    if limit:
        limit = int(limit)
        res_page = res_page[:limit] if limit < len(res_page) else res_page

    marker = job_execution_get(context, marker)
    prev_marker, next_marker = _get_prev_and_next_objects(
        res, limit, marker)
    return types.Page(res_page, prev_marker, next_marker)


def job_execution_count(context, **kwargs):
    query = count_query(m.JobExecution, context)
    return query.filter_by(**kwargs).first()[0]


def _get_config_section(configs, mapping_type):
    if mapping_type not in configs:
        configs[mapping_type] = [] if mapping_type == "args" else {}
    return configs[mapping_type]


def _merge_execution_interface(job_ex, job, execution_interface):
    """Merges the interface for a job execution with that of its job."""
    configs = job_ex.job_configs or {}
    nonexistent = object()
    positional_args = {}
    for arg in job.interface:
        value = nonexistent
        typed_configs = _get_config_section(configs, arg.mapping_type)
        # Interface args are our first choice for the value.
        if arg.name in execution_interface:
            value = execution_interface[arg.name]
        else:
            # If a default exists, we can use that, but...
            if arg.default is not None:
                value = arg.default
            # We should prefer an argument passed through the
            # job_configs that maps to the same location.
            if arg.mapping_type != "args":
                value = typed_configs.get(arg.location, value)
        if value is not nonexistent:
            if arg.mapping_type != "args":
                typed_configs[arg.location] = value
            else:
                positional_args[int(arg.location)] = value
    if positional_args:
        positional_args = [positional_args[i] for i
                           in range(len(positional_args))]
        configs["args"] = positional_args + configs["args"]
    if configs and not job_ex.job_configs:
        job_ex.job_configs = configs


def job_execution_create(context, values):
    session = get_session()
    execution_interface = values.pop('interface', {})
    job_ex = m.JobExecution()
    job_ex.update(values)

    try:
        with session.begin():
            job_ex.interface = []
            job = _job_get(context, session, job_ex.job_id)
            if job.interface:
                _merge_execution_interface(job_ex, job, execution_interface)
            session.add(job_ex)
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
        session.add(job_ex)

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


def job_get_all(context, regex_search=False,
                limit=None, marker=None, sort_by=None, **kwargs):

    regex_cols = ['name', 'description']
    sort_by, order = _parse_sorting_args(sort_by)
    query = model_query(m.Job, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.Job, regex_cols, kwargs)

    limit = int(limit) if limit else None
    marker = job_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(query.filter_by(**kwargs),
                                  m.Job, limit, [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def _append_job_binaries(context, session, from_list, to_list):
    for job_binary_id in from_list:
        job_binary = model_query(
            m.JobBinary, context, session).filter_by(id=job_binary_id).first()
        if job_binary is not None:
            to_list.append(job_binary)


def _append_interface(context, from_list, to_list):
    for order, argument_values in enumerate(from_list):
        argument_values['tenant_id'] = context.tenant_id
        argument_values['order'] = order
        argument = m.JobInterfaceArgument()
        argument.update(argument_values)
        to_list.append(argument)


def job_create(context, values):
    mains = values.pop("mains", [])
    libs = values.pop("libs", [])
    interface = values.pop("interface", [])

    session = get_session()
    try:
        with session.begin():
            job = m.Job()
            job.update(values)
            # These are 'lazy' objects. The initialization below
            # is needed here because it provides libs, mains, and
            # interface to be initialized within a session even if
            # the lists are empty
            job.mains = []
            job.libs = []
            job.interface = []

            _append_job_binaries(context, session, mains, job.mains)
            _append_job_binaries(context, session, libs, job.libs)
            _append_interface(context, interface, job.interface)

            session.add(job)

    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for Job: %s") % e.columns)

    return job


def job_update(context, job_id, values):
    session = get_session()
    try:
        with session.begin():
            job = _job_get(context, session, job_id)
            if not job:
                raise ex.NotFoundException(job_id,
                                           _("Job id '%s' not found!"))

            validate.check_tenant_for_update(context, job)
            validate.check_protected_from_update(job, values)

            job.update(values)
            session.add(job)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for Job: %s") % e.columns)

    return job


def job_destroy(context, job_id):
    session = get_session()
    try:
        with session.begin():
            job = _job_get(context, session, job_id)
            if not job:
                raise ex.NotFoundException(job_id,
                                           _("Job id '%s' not found!"))

            validate.check_tenant_for_delete(context, job)
            validate.check_protected_from_delete(job)

            session.delete(job)
    except db_exc.DBError as e:
        msg = ("foreign key constraint" in six.text_type(e) and
               _(" on foreign key constraint") or "")
        raise ex.DeletionFailed(_("Job deletion failed%s") % msg)


# JobBinary ops

def _job_binary_get(context, session, job_binary_id):
    query = model_query(m.JobBinary, context, session)
    return query.filter_by(id=job_binary_id).first()


def job_binary_get_all(context, regex_search=False,
                       limit=None, marker=None, sort_by=None, **kwargs):

    sort_by, order = _parse_sorting_args(sort_by)

    regex_cols = ['name', 'description', 'url']
    query = model_query(m.JobBinary, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.JobBinary, regex_cols, kwargs)

    limit = int(limit) if limit else None
    marker = job_binary_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(query.filter_by(**kwargs),
                                  m.JobBinary,
                                  limit, [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def job_binary_get(context, job_binary_id):
    """Returns a JobBinary object that does not contain a data field

    The data column uses deferred loading.
    """
    return _job_binary_get(context, get_session(), job_binary_id)


def job_binary_create(context, values):
    """Returns a JobBinary that does not contain a data field

    The data column uses deferred loading.
    """
    job_binary = m.JobBinary()
    job_binary.update(values)

    session = get_session()
    try:
        with session.begin():
            session.add(job_binary)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for JobBinary: %s") % e.columns)

    return job_binary


def job_binary_update(context, values):
    """Returns a JobBinary updated with the provided values."""
    jb_id = values["id"]
    session = get_session()
    try:
        with session.begin():
            jb = _job_binary_get(context, session, jb_id)
            if not jb:
                raise ex.NotFoundException(
                    jb_id, _("JobBinary id '%s' not found"))

            validate.check_tenant_for_update(context, jb)
            validate.check_protected_from_update(jb, values)

            # We do not want to update the url for internal binaries
            new_url = values.get("url", None)
            if new_url and "internal-db://" in jb["url"]:
                if jb["url"] != new_url:
                    raise ex.UpdateFailedException(
                        jb_id,
                        _("The url for JobBinary Id '%s' can not "
                          "be updated because it is an internal-db url."))
            jobs = job_execution_get_all(context)
            pending_jobs = [job for job in jobs if
                            job.info["status"] == "PENDING"]
            if len(pending_jobs) > 0:
                for job in pending_jobs:
                    if _check_job_binary_referenced(
                            context, session, jb_id, job.job_id):
                        raise ex.UpdateFailedException(
                            jb_id,
                            _("JobBinary Id '%s' is used in a PENDING job "
                              "and can not be updated."))
            jb.update(values)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for JobBinary: %s") % e.columns)

    return jb


def _check_job_binary_referenced(ctx, session, job_binary_id, job_id=None):
    args = {"JobBinary_id": job_binary_id}
    if job_id:
        args["Job_id"] = job_id
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

        validate.check_tenant_for_delete(context, job_binary)
        validate.check_protected_from_delete(job_binary)

        if _check_job_binary_referenced(context, session, job_binary_id):
            raise ex.DeletionFailed(
                _("JobBinary is referenced and cannot be deleted"))

        session.delete(job_binary)


# JobBinaryInternal ops

def _job_binary_internal_get(context, session, job_binary_internal_id):
    query = model_query(m.JobBinaryInternal, context, session)
    return query.filter_by(id=job_binary_internal_id).first()


def job_binary_internal_get_all(context, regex_search=False, limit=None,
                                marker=None, sort_by=None, **kwargs):
    """Returns JobBinaryInternal objects that do not contain a data field

    The data column uses deferred loading.
    """
    sort_by, order = _parse_sorting_args(sort_by)

    regex_cols = ['name']

    query = model_query(m.JobBinaryInternal, context)
    if regex_search:
        query, kwargs = regex_filter(query,
                                     m.JobBinaryInternal, regex_cols, kwargs)

    limit = int(limit) if limit else None
    marker = job_binary_internal_get(context, marker)

    prev_marker, next_marker = _get_prev_and_next_objects(
        query.filter_by(**kwargs).order_by(sort_by).all(),
        limit, marker, order=order)

    result = utils.paginate_query(query.filter_by(**kwargs),
                                  m.JobBinaryInternal, limit,
                                  [sort_by], marker, order)

    return types.Page(result, prev_marker, next_marker)


def job_binary_internal_get(context, job_binary_internal_id):
    """Returns a JobBinaryInternal object that does not contain a data field

    The data column uses deferred loading.
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
    try:
        with session.begin():
            session.add(job_binary_int)
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

        validate.check_tenant_for_delete(context, job_binary_internal)
        validate.check_protected_from_delete(job_binary_internal)

        session.delete(job_binary_internal)


def job_binary_internal_update(context, job_binary_internal_id, values):
    """Returns a JobBinary updated with the provided values."""
    session = get_session()
    try:
        with session.begin():
            j_b_i = _job_binary_internal_get(
                context, session, job_binary_internal_id)
            if not j_b_i:
                raise ex.NotFoundException(
                    job_binary_internal_id,
                    _("JobBinaryInternal id '%s' not found!"))

            validate.check_tenant_for_update(context, j_b_i)
            validate.check_protected_from_update(j_b_i, values)

            j_b_i.update(values)
    except db_exc.DBDuplicateEntry as e:
        raise ex.DBDuplicateEntry(
            _("Duplicate entry for JobBinaryInternal: %s") % e.columns)

    return j_b_i


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


# Cluster verifications / health check ops

def _cluster_verification_get(context, session, verification_id):
    # tenant id is not presented
    query = model_query(m.ClusterVerification, context, session,
                        project_only=False)
    return query.filter_by(id=verification_id).first()


def cluster_verification_get(context, verification_id):
    return _cluster_verification_get(context, get_session(), verification_id)


def cluster_verification_add(context, cluster_id, values):
    session = get_session()

    with session.begin():
        cluster = _cluster_get(context, session, cluster_id)

        if not cluster:
            raise ex.NotFoundException(
                cluster_id, _("Cluster id '%s' not found!"))

        verification = m.ClusterVerification()
        values['cluster_id'] = cluster_id
        verification.update(values)
        session.add(verification)

    return _cluster_verification_get(context, session, verification.id)


def cluster_verification_update(context, verification_id, values):
    session = get_session()

    with session.begin():
        verification = _cluster_verification_get(
            context, session, verification_id)

        if not verification:
            raise ex.NotFoundException(
                verification_id, _("Verification id '%s' not found!"))

        verification.update(values)
    return verification


def cluster_verification_delete(context, verification_id):
    session = get_session()

    with session.begin():
        verification = _cluster_verification_get(
            context, session, verification_id)

        if not verification:
            raise ex.NotFoundException(
                verification_id, _("Verification id '%s' not found!"))

        for check in verification.checks:
            session.delete(check)

        session.delete(verification)


def _cluster_health_check_get(context, session, health_check_id):
    # tenant id is not presented
    query = model_query(m.ClusterHealthCheck, context, session,
                        project_only=False)
    return query.filter_by(id=health_check_id).first()


def cluster_health_check_get(context, health_check_id):
    return _cluster_health_check_get(context, get_session(), health_check_id)


def cluster_health_check_add(context, verification_id, values):
    session = get_session()

    with session.begin():
        verification = _cluster_verification_get(
            context, session, verification_id)

        if not verification:
            raise ex.NotFoundException(
                verification_id, _("Verification id '%s' not found!"))

        health_check = m.ClusterHealthCheck()
        values['verification_id'] = verification_id
        values['tenant_id'] = context.tenant_id
        health_check.update(values)
        session.add(health_check)

    return health_check


def cluster_health_check_update(context, health_check_id, values):
    session = get_session()

    with session.begin():
        health_check = _cluster_health_check_get(
            context, session, health_check_id)

        if not health_check:
            raise ex.NotFoundException(
                health_check_id, _("Health check id '%s' not found!"))

        health_check.update(values)

    return health_check


def _plugin_get(context, session, name):
    query = model_query(m.PluginData, context, session)
    return query.filter_by(name=name).first()


def plugin_get(context, name):
    session = get_session()
    with session.begin():
        data = _plugin_get(context, session, name)
    return data


def plugin_create(context, values):
    session = get_session()
    with session.begin():
        plugin = m.PluginData()
        values['tenant_id'] = context.tenant_id
        plugin.update(values)
        session.add(plugin)
    return plugin


def plugin_get_all(context):
    query = model_query(m.PluginData, context)
    return query.all()


def plugin_update(context, name, values):
    session = get_session()

    with session.begin():
        plugin = _plugin_get(context, session, name)

        if not plugin:
            raise ex.NotFoundException(name, _("Plugin name '%s' not found!"))

        plugin.update(values)

    return plugin


def plugin_remove(context, name):
    session = get_session()

    with session.begin():
        plugin = _plugin_get(context, session, name)

        if not plugin:
            raise ex.NotFoundException(name, _("Plugin name '%s' not found!"))

        session.delete(plugin)
