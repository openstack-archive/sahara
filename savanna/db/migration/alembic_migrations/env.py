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

from alembic import context
from logging import config as logging_config
from savanna.openstack.common import importutils
from sqlalchemy import create_engine, pool

from savanna.db import model_base


importutils.import_module('savanna.db.models')

config = context.config
savanna_config = config.savanna_config

logging_config.fileConfig(config.config_file_name)

# set the target for 'autogenerate' support
target_metadata = model_base.SavannaBase.metadata


def run_migrations_offline():
    context.configure(url=savanna_config.database.connection)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(savanna_config.database.connection,
                           poolclass=pool.NullPool)

    connection = engine.connect()
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    try:
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
