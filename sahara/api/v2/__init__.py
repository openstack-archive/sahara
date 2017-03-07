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

"""
v2 API interface package

This package contains the endpoint definitions for the version 2 API.
The modules in this package are named in accordance with the top-level
resource primitives they represent.

This module provides a convenience function to register all the
endpoint blueprints to the ``/v2`` root.

When creating new endpoint modules, the following steps should be taken
to ensure they are properly registered with the Flask application:
  * create the module file with a name that indicates its endpoint
  * add a sahara.utils.api.RestV2 blueprint object
  * add an import to this module (__init__.py)
  * add a registration line for the new endpoint to the
    register_blueprint function
"""

from sahara.api.v2 import cluster_templates
from sahara.api.v2 import clusters
from sahara.api.v2 import data_sources
from sahara.api.v2 import images
from sahara.api.v2 import job_binaries
from sahara.api.v2 import job_templates
from sahara.api.v2 import job_types
from sahara.api.v2 import jobs
from sahara.api.v2 import node_group_templates
from sahara.api.v2 import plugins


def register_blueprints(app, url_prefix):
    """Register the v2 endpoints with a Flask application

    This function will take a Flask application object and register all
    the v2 endpoints. Register blueprints here when adding new endpoint
    modules.

    :param app: A Flask application object to register blueprints on
    :param url_prefix: The url prefix for the blueprints
    """
    app.register_blueprint(cluster_templates.rest, url_prefix=url_prefix)
    app.register_blueprint(clusters.rest, url_prefix=url_prefix)
    app.register_blueprint(data_sources.rest, url_prefix=url_prefix)
    app.register_blueprint(images.rest, url_prefix=url_prefix)
    app.register_blueprint(job_binaries.rest, url_prefix=url_prefix)
    app.register_blueprint(jobs.rest, url_prefix=url_prefix)
    app.register_blueprint(job_types.rest, url_prefix=url_prefix)
    app.register_blueprint(job_templates.rest, url_prefix=url_prefix)
    app.register_blueprint(node_group_templates.rest, url_prefix=url_prefix)
    app.register_blueprint(plugins.rest, url_prefix=url_prefix)
