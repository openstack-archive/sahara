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

from flask.ext.sqlalchemy import SQLAlchemy
from oslo.config import cfg

DB = SQLAlchemy()

opts = [
    cfg.StrOpt('database_uri',
               default='sqlite:////tmp/savanna.db',
               help='URL for sqlalchemy database'),
    cfg.BoolOpt('echo',
                default=False,
                help='Sqlalchemy echo')
]

CONF = cfg.CONF
CONF.register_opts(opts, group='sqlalchemy')


def setup_storage(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = CONF.sqlalchemy.database_uri
    app.config['SQLALCHEMY_ECHO'] = CONF.sqlalchemy.echo

    DB.app = app
    DB.init_app(app)
    DB.create_all()
