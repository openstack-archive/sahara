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

from oslo_config import cfg
from oslo_log import log as logging
import six

from sahara import conductor as c
from sahara import context
from sahara import exceptions as ex
from sahara.plugins import base as plugin_base
from sahara.service import api
from sahara.service.edp.binary_retrievers import dispatch
from sahara.service.edp import job_manager as manager
from sahara.utils import edp
from sahara.utils import proxy as p


conductor = c.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_job_types(**kwargs):
    # Return a dictionary of all the job types that can be run
    # by this instance of Sahara. For each job type, the value
    # will be a list of plugins that support the job type. For
    # each plugin, include a dictionary of the versions that
    # support the job type.

    # All entries in kwargs are expected to have list values
    hints = kwargs.get("hints", ["false"])[0].lower() == "true"

    plugin_names = kwargs.get("plugin", [])
    all_plugins = plugin_base.PLUGINS.get_plugins()
    if plugin_names:
        plugins = filter(lambda x: x.name in plugin_names, all_plugins)
    else:
        plugins = all_plugins

    job_types = kwargs.get("type", edp.JOB_TYPES_ALL)
    versions = kwargs.get("version", [])

    res = []

    for job_type in job_types:
        # All job types supported by all versions of the plugin.
        # This is a dictionary where keys are plugin version
        # strings and values are lists of job types
        job_entry = {"name": job_type,
                     "plugins": []}

        for plugin in plugins:
            types_for_plugin = plugin.get_edp_job_types(versions)

            # dict returns a new object so we are not modifying the plugin
            p = plugin.dict

            # Find only the versions of this plugin that support the job.
            # Additionally, instead of a list we want a dictionary of
            # plugin versions with corresponding config hints
            p["versions"] = {}

            for version, supported_types in six.iteritems(types_for_plugin):
                if job_type in supported_types:
                    if hints:
                        config_hints = plugin.get_edp_config_hints(job_type,
                                                                   version)
                    else:
                        config_hints = {}
                    p["versions"][version] = config_hints

            # If we found at least one version of the plugin that
            # supports the job type, add the plugin to the result
            if p["versions"]:
                job_entry["plugins"].append(p)

        if job_entry["plugins"]:
            res.append(job_entry)
    return res


def get_job_config_hints(job_type):
    return manager.get_job_config_hints(job_type)


def execute_job(job_id, data):
    # Elements common to all job types
    cluster_id = data['cluster_id']
    configs = data.get('job_configs', {})
    interface = data.get('interface', {})

    # Not in Java job types but present for all others
    input_id = data.get('input_id', None)
    output_id = data.get('output_id', None)

    # Since we will use a unified class in the database, we pass
    # a superset for all job types
    # example configs['start'] = '2015-05-12T08:55Z' frequency = 5 mins
    # the job will starts from 2015-05-12T08:55Z, runs every 5 mins

    job_execution_info = data.get('job_execution_info', {})

    configs['job_execution_info'] = job_execution_info

    job_ex_dict = {'input_id': input_id, 'output_id': output_id,
                   'job_id': job_id, 'cluster_id': cluster_id,
                   'info': {'status': edp.JOB_STATUS_PENDING},
                   'job_configs': configs, 'extra': {},
                   'interface': interface}
    job_execution = conductor.job_execution_create(context.ctx(), job_ex_dict)
    context.set_current_job_execution_id(job_execution.id)

    # check to use proxy user
    if p.job_execution_requires_proxy_user(job_execution):
        try:
            p.create_proxy_user_for_job_execution(job_execution)
        except ex.SaharaException as e:
            LOG.error("Can't run job execution. "
                      "(Reasons: {reason})".format(reason=e))
            conductor.job_execution_destroy(context.ctx(), job_execution)
            raise

    api.OPS.run_edp_job(job_execution.id)

    return job_execution


def get_job_execution_status(id):
    return manager.get_job_status(id)


def job_execution_list(**kwargs):
    return conductor.job_execution_get_all(context.ctx(),
                                           regex_search=True, **kwargs)


def get_job_execution(id):
    return conductor.job_execution_get(context.ctx(), id)


def cancel_job_execution(id):
    context.set_current_job_execution_id(id)
    job_execution = conductor.job_execution_get(context.ctx(), id)
    api.OPS.cancel_job_execution(id)

    return job_execution


def update_job_execution(id, values):
    _update_status(values.pop("info", None), id)
    return conductor.job_execution_update(context.ctx(), id, values)


def _update_status(info, id):
    if info:
        status = info.get("status", None)
        if status == edp.JOB_ACTION_SUSPEND:
            api.OPS.job_execution_suspend(id)


def delete_job_execution(id):
    context.set_current_job_execution_id(id)
    api.OPS.delete_job_execution(id)


def get_data_sources(**kwargs):
    return conductor.data_source_get_all(context.ctx(),
                                         regex_search=True, **kwargs)


def get_data_source(id):
    return conductor.data_source_get(context.ctx(), id)


def delete_data_source(id):
    conductor.data_source_destroy(context.ctx(), id)


def register_data_source(values):
    return conductor.data_source_create(context.ctx(), values)


def data_source_update(id, values):
    return conductor.data_source_update(context.ctx(), id, values)


def get_jobs(**kwargs):
    return conductor.job_get_all(context.ctx(), regex_search=True, **kwargs)


def get_job(id):
    return conductor.job_get(context.ctx(), id)


def create_job(values):
    return conductor.job_create(context.ctx(), values)


def update_job(id, values):
    return conductor.job_update(context.ctx(), id, values)


def delete_job(job_id):
    return conductor.job_destroy(context.ctx(), job_id)


def create_job_binary(values):
    return conductor.job_binary_create(context.ctx(), values)


def get_job_binaries(**kwargs):
    return conductor.job_binary_get_all(context.ctx(),
                                        regex_search=True, **kwargs)


def get_job_binary(id):
    return conductor.job_binary_get(context.ctx(), id)


def update_job_binary(id, values):
    return conductor.job_binary_update(context.ctx(), id, values)


def delete_job_binary(id):
    conductor.job_binary_destroy(context.ctx(), id)


def create_job_binary_internal(values):
    return conductor.job_binary_internal_create(context.ctx(), values)


def get_job_binary_internals(**kwargs):
    return conductor.job_binary_internal_get_all(context.ctx(),
                                                 regex_search=True, **kwargs)


def get_job_binary_internal(id):
    return conductor.job_binary_internal_get(context.ctx(), id)


def delete_job_binary_internal(id):
    conductor.job_binary_internal_destroy(context.ctx(), id)


def get_job_binary_internal_data(id):
    return conductor.job_binary_internal_get_raw_data(context.ctx(), id)


def update_job_binary_internal(id, values):
    return conductor.job_binary_internal_update(context.ctx(), id, values)


def get_job_binary_data(id):
    job_binary = conductor.job_binary_get(context.ctx(), id)
    return dispatch.get_raw_binary(job_binary, with_context=True)
