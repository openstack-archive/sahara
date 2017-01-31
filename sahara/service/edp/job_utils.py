# Copyright (c) 2014 OpenStack Foundation
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
from oslo_utils import uuidutils
import six

from sahara import conductor as c
from sahara import context
from sahara.plugins import base as plugin_base
from sahara.service.edp.data_sources import manager as ds_manager
from sahara.service.edp.utils import shares as shares_service
from sahara.utils import remote


opts = [
    cfg.StrOpt('job_workflow_postfix',
               default='',
               help="Postfix for storing jobs in hdfs. Will be "
                    "added to '/user/<hdfs user>/' path.")
]

CONF = cfg.CONF
CONF.register_opts(opts)

conductor = c.API

# Prefix used to mark data_source name references in arg lists
DATA_SOURCE_PREFIX = "datasource://"

DATA_SOURCE_SUBST_NAME = "edp.substitute_data_source_for_name"
DATA_SOURCE_SUBST_UUID = "edp.substitute_data_source_for_uuid"


def get_plugin(cluster):
    return plugin_base.PLUGINS.get_plugin(cluster.plugin_name)


def get_data_source(ds_name):
    return ds_manager.DATA_SOURCES.get_data_source(ds_name)


def create_workflow_dir(where, path, job, use_uuid=None, chmod=""):

    if use_uuid is None:
        use_uuid = uuidutils.generate_uuid()

    constructed_dir = _append_slash_if_needed(path)
    constructed_dir += '%s/%s' % (job.name, use_uuid)
    with remote.get_remote(where) as r:
        if chmod:
            r.execute_command("mkdir -p -m %s %s" % (chmod, constructed_dir))
        else:
            r.execute_command("mkdir -p %s" % constructed_dir)
    return constructed_dir


def _get_data_source_urls(ds, cluster, job_exec_id):
    # returns a tuple (native_url, runtime_url)
    return get_data_source(ds.type).get_urls(ds.url, cluster, job_exec_id)


def get_input_output_data_sources(job_execution, job, data_source_urls,
                                  cluster=None):
    def _construct(ctx, ds_id):
        job_exec_id = job_execution.id
        source = conductor.data_source_get(ctx, ds_id)
        if source and source.id not in data_source_urls:
            data_source_urls[source.id] = _get_data_source_urls(source,
                                                                cluster,
                                                                job_exec_id)
        return source

    ctx = context.ctx()
    input_source = _construct(ctx, job_execution.input_id)
    output_source = _construct(ctx, job_execution.output_id)

    return input_source, output_source


def _append_slash_if_needed(path):
    if path[-1] != '/':
        path += '/'
    return path


def may_contain_data_source_refs(job_configs):

    def _check_data_source_ref_option(option):
        truth = job_configs and (
            job_configs.get('configs', {}).get(option))
        # Config values specified in the UI may be
        # passed as strings
        return truth in (True, 'True')

    return (
        _check_data_source_ref_option(DATA_SOURCE_SUBST_NAME),
        _check_data_source_ref_option(DATA_SOURCE_SUBST_UUID))


def _data_source_ref_search(job_configs, func, prune=lambda x: x):
    """Return a list of unique values in job_configs filtered by func().

    Loop over the 'args', 'configs' and 'params' elements in
    job_configs and return a list of all values for which
    func(value) is True.

    Optionally provide a 'prune' function that is applied
    to values before they are added to the return value.
    """
    args = set([prune(arg) for arg in job_configs.get(
        'args', []) if func(arg)])

    configs = set([prune(val) for val in six.itervalues(
        job_configs.get('configs', {})) if func(val)])

    params = set([prune(val) for val in six.itervalues(
        job_configs.get('params', {})) if func(val)])

    return list(args | configs | params)


def find_possible_data_source_refs_by_name(job_configs):
    """Find string values in job_configs starting with 'datasource://'.

    Loop over the 'args', 'configs', and 'params' elements of
    job_configs to find all values beginning with the prefix
    'datasource://'. Return a list of unique values with the prefix
    removed.

    Note that for 'configs' and 'params', which are dictionaries, only
    the values are considered and the keys are not relevant.
    """
    def startswith(arg):
        return isinstance(
            arg,
            six.string_types) and arg.startswith(DATA_SOURCE_PREFIX)
    return _data_source_ref_search(job_configs,
                                   startswith,
                                   prune=lambda x: x[len(DATA_SOURCE_PREFIX):])


def find_possible_data_source_refs_by_uuid(job_configs):
    """Find string values in job_configs which are uuids.

    Return a list of unique values in the 'args', 'configs', and 'params'
    elements of job_configs which have the form of a uuid.

    Note that for 'configs' and 'params', which are dictionaries, only
    the values are considered and the keys are not relevant.
    """
    return _data_source_ref_search(job_configs, uuidutils.is_uuid_like)


def resolve_data_source_references(job_configs,
                                   job_exec_id,
                                   data_source_urls,
                                   cluster=None):
    """Resolve possible data_source references in job_configs.

    Look for any string values in the 'args', 'configs', and 'params'
    elements of job_configs which start with 'datasource://' or have
    the form of a uuid.

    For values beginning with 'datasource://', strip off the prefix
    and search for a DataSource object with a name that matches the
    value.

    For values having the form of a uuid, search for a DataSource object
    with an id that matches the value.

    If a DataSource object is found for the value, replace the value
    with the URL from the DataSource object. If any DataSource objects
    are found which reference swift paths and contain credentials, set
    credential configuration values in job_configs (use the first set
    of swift credentials found).

    If no values are resolved, return an empty list and a reference
    to job_configs.

    If any values are resolved, return a list of the referenced
    data_source objects and a copy of job_configs with all of the
    references replaced with URLs.
    """
    by_name, by_uuid = may_contain_data_source_refs(job_configs)
    if not (by_name or by_uuid):
        return [], job_configs

    ctx = context.ctx()
    ds_seen = {}
    new_configs = {}

    def _resolve(value):
        kwargs = {}
        if by_name and isinstance(
                value,
                six.string_types) and value.startswith(DATA_SOURCE_PREFIX):
            value = value[len(DATA_SOURCE_PREFIX):]
            kwargs['name'] = value

        elif by_uuid and uuidutils.is_uuid_like(value):
            kwargs['id'] = value

        if kwargs:
            # Name and id are both unique constraints so if there
            # is more than 1 something is really wrong
            ds = conductor.data_source_get_all(ctx, **kwargs)
            if len(ds) == 1:
                ds = ds[0]
                ds_seen[ds.id] = ds
                if ds.id not in data_source_urls:
                    data_source_urls[ds.id] = _get_data_source_urls(
                        ds, cluster, job_exec_id)
                return data_source_urls[ds.id][1]
        return value

    # Loop over configs/params/args and look up each value as a data_source.
    # If we find it, replace the value. In all cases, we've produced a
    # copy which is not a FrozenClass type and can be updated.
    new_configs['configs'] = {
        k: _resolve(v) for k, v in six.iteritems(
            job_configs.get('configs', {}))}
    new_configs['params'] = {
        k: _resolve(v) for k, v in six.iteritems(
            job_configs.get('params', {}))}
    new_configs['args'] = [_resolve(a) for a in job_configs.get('args', [])]

    # If we didn't resolve anything we might as well return the original
    ds_seen = ds_seen.values()
    if not ds_seen:
        return [], job_configs

    # If there are proxy_configs we'll need to copy these, too,
    # so job_configs is complete
    if job_configs.get('proxy_configs'):
        new_configs['proxy_configs'] = {
            k: v for k, v in six.iteritems(job_configs.get('proxy_configs'))}

    return ds_seen, new_configs


def prepare_cluster_for_ds(data_sources, cluster, job_configs, ds_urls):
    for ds in data_sources:
        if ds:
            get_data_source(ds.type).prepare_cluster(
                ds, cluster, job_configs=job_configs,
                runtime_url=ds_urls[ds.id])


def to_url_dict(data_source_urls, runtime=False):
    idx = 1 if runtime else 0
    return {id: urls[idx] for id, urls in six.iteritems(data_source_urls)}


def mount_share_at_default_path(url, cluster):
    # Automount this share to the cluster with default path
    # url example: 'manila://ManilaShare-uuid/path_to_file'
    share_id = six.moves.urllib.parse.urlparse(url).netloc
    if cluster.shares:
        cluster_shares = [dict(s) for s in cluster.shares]
    else:
        cluster_shares = []

    needed_share = {
        'id': share_id,
        'path': shares_service.default_mount(share_id),
        'access_level': 'rw'
    }

    cluster_shares.append(needed_share)
    cluster = conductor.cluster_update(
        context.ctx(), cluster, {'shares': cluster_shares})
    shares_service.mount_shares(cluster)

    return shares_service.get_share_path(url, cluster.shares)
