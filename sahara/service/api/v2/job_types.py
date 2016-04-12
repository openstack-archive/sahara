# Copyright (c) 2016 Red Hat, Inc.
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

import six

from sahara.plugins import base as plugin_base
from sahara.utils import edp


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
