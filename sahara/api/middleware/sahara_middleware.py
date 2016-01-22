# Copyright (c) 2015 Mirantis Inc.
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

import flask
from oslo_config import cfg
import six
from werkzeug import exceptions as werkzeug_exceptions

from sahara.api import v10 as api_v10
from sahara.api import v11 as api_v11
from sahara.api import v2 as api_v2
from sahara import context
from sahara.utils import api as api_utils


CONF = cfg.CONF


def build_app(version_response=None):
    """App builder (wsgi).

    Entry point for Sahara REST API server
    """
    app = flask.Flask('sahara.api')

    version_response = (version_response or
                        {
                            "versions": [
                                {"id": "v1.0", "status": "SUPPORTED"},
                                {"id": "v1.1", "status": "CURRENT"}
                            ]
                        })

    @app.route('/', methods=['GET'])
    def version_list():
        context.set_ctx(None)
        return api_utils.render(version_response)

    @app.teardown_request
    def teardown_request(_ex=None):
        context.set_ctx(None)

    app.register_blueprint(api_v10.rest, url_prefix='/v1.0')
    app.register_blueprint(api_v10.rest, url_prefix='/v1.1')
    app.register_blueprint(api_v11.rest, url_prefix='/v1.1')

    def make_json_error(ex):
        status_code = (ex.code
                       if isinstance(ex, werkzeug_exceptions.HTTPException)
                       else 500)
        description = (ex.description
                       if isinstance(ex, werkzeug_exceptions.HTTPException)
                       else str(ex))
        return api_utils.render({'error': status_code,
                                 'error_message': description},
                                status=status_code)

    for code in six.iterkeys(werkzeug_exceptions.default_exceptions):
        app.error_handler_spec[None][code] = make_json_error

    return app


def build_v2_app():
    """App builder (wsgi).

    Entry point for Experimental V2 Sahara REST API server
    """
    version_response = {
        "versions": [
            {"id": "v1.0", "status": "SUPPORTED"},
            {"id": "v1.1", "status": "CURRENT"},
            {"id": "v2", "status": "EXPERIMENTAL"}
        ]
    }
    app = build_app(version_response)

    api_v2.register_blueprints(app, url_prefix='/v2')

    return app


class Router(object):
    def __call__(self, environ, response):
        return self.app(environ, response)

    @classmethod
    def factory(cls, global_config, **local_config):
        cls.app = build_app()
        return cls(**local_config)


class RouterV2(object):
    def __call__(self, environ, response):
        return self.app(environ, response)

    @classmethod
    def factory(cls, global_config, **local_config):
        cls.app = build_v2_app()
        return cls(**local_config)
