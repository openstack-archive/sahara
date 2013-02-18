from eho.server.storage.defaults import setup_defaults
from eho.server.utils.api import render

from flask import Flask
from eho.server.api import v01 as api_v01
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from eho.server.storage.storage import setup_storage
from eho.server.scheduler import setup_scheduler


def make_app():
    """
    Entry point for Elastic Hadoop on OpenStack REST API server
    """
    app = Flask('eho.api')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eho-server.db'
    app.config['SQLALCHEMY_ECHO'] = True

    app.register_blueprint(api_v01.rest, url_prefix='/v0.1')
    setup_storage(app)
    setup_scheduler()
    setup_defaults()

    def make_json_error(ex):
        status_code = (ex.code
                       if isinstance(ex, HTTPException)
                       else 500)
        description = (ex.description
                       if isinstance(ex, HTTPException)
                       else str(ex))
        return render({'error': status_code, 'error_message': description},
                      status=status_code)

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    return app
