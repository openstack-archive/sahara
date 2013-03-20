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

CONF = cfg.CONF
CONF.import_opt('reset_db', 'savanna.config')


def setup_storage(app):
    DB.app = app
    DB.init_app(app)

    if CONF.reset_db:
        DB.drop_all()

    DB.create_all()
