# Copyright 2010-2011 OpenStack Foundation
# Copyright 2012-2013 IBM Corp.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
#
# Ripped off from Nova's test_migrations.py
# The only difference between Nova and this code is usage of alembic instead
# of sqlalchemy migrations.
#
# There is an ongoing work to extact similar code to oslo incubator. Once it is
# extracted we'll be able to remove this file and use oslo.

import io
import os

import alembic
from alembic import command
from alembic import config as alembic_config
from alembic import migration
from alembic import script as alembic_script
from oslo_config import cfg
from oslo_db.sqlalchemy import test_migrations as t_m
from oslo_log import log as logging

import sahara.db.migration
from sahara.db.sqlalchemy import api as sa
from sahara.db.sqlalchemy import model_base


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseWalkMigrationTestCase(object):

    ALEMBIC_CONFIG = alembic_config.Config(
        os.path.join(os.path.dirname(sahara.db.migration.__file__),
                     'alembic.ini')
    )

    ALEMBIC_CONFIG.sahara_config = CONF

    def _configure(self, engine):
        """For each type of repository we should do some of configure steps.

        For migrate_repo we should set under version control our database.
        For alembic we should configure database settings. For this goal we
        should use oslo_config and openstack.commom.db.sqlalchemy.session with
        database functionality (reset default settings and session cleanup).
        """
        CONF.set_override('connection', str(engine.url), group='database')
        sa.cleanup()

    def _alembic_command(self, alembic_command, engine, *args, **kwargs):
        """Most of alembic command return data into output.

        We should redefine this setting for getting info.
        """
        self.ALEMBIC_CONFIG.stdout = buf = io.StringIO()
        CONF.set_override('connection', str(engine.url), group='database')
        sa.cleanup()
        getattr(command, alembic_command)(*args, **kwargs)
        res = buf.getvalue().strip()
        LOG.debug('Alembic command {command} returns: {result}'.format(
                  command=alembic_command, result=res))
        sa.cleanup()
        return res

    def _get_versions(self):
        """Stores a list of versions.

        Since alembic version has a random algorithm of generation
        (SA-migrate has an ordered autoincrement naming) we should store
        a list of versions (version for upgrade)
        for successful testing of migrations in up mode.
        """

        env = alembic_script.ScriptDirectory.from_config(self.ALEMBIC_CONFIG)
        versions = []
        for rev in env.walk_revisions():
            versions.append(rev.revision)

        versions.reverse()
        return versions

    def walk_versions(self, engine=None):
        # Determine latest version script from the repo, then
        # upgrade from 1 through to the latest, with no data
        # in the databases. This just checks that the schema itself
        # upgrades successfully.

        self._configure(engine)
        versions = self._get_versions()
        for ver in versions:
            self._migrate_up(engine, ver, with_data=True)

    def _get_version_from_db(self, engine):
        """Returns latest version from db for each type of migrate repo."""

        conn = engine.connect()
        try:
            context = migration.MigrationContext.configure(conn)
            version = context.get_current_revision() or '-1'
        finally:
            conn.close()
        return version

    def _migrate(self, engine, version, cmd):
        """Base method for manipulation with migrate repo.

        It will upgrade or downgrade the actual database.
        """

        self._alembic_command(cmd, engine, self.ALEMBIC_CONFIG, version)

    def _migrate_up(self, engine, version, with_data=False):
        """migrate up to a new version of the db.

        We allow for data insertion and post checks at every
        migration version with special _pre_upgrade_### and
        _check_### functions in the main test.
        """
        # NOTE(sdague): try block is here because it's impossible to debug
        # where a failed data migration happens otherwise
        check_version = version
        try:
            if with_data:
                data = None
                pre_upgrade = getattr(
                    self, "_pre_upgrade_%s" % check_version, None)
                if pre_upgrade:
                    data = pre_upgrade(engine)
            self._migrate(engine, version, 'upgrade')
            self.assertEqual(version, self._get_version_from_db(engine))
            if with_data:
                check = getattr(self, "_check_%s" % check_version, None)
                if check:
                    check(engine, data)
        except Exception:
            LOG.error("Failed to migrate to version {version} on engine "
                      "{engine}".format(version=version, engine=engine))
            raise


class TestModelsMigrationsSync(t_m.ModelsMigrationsSync):
    """Class for comparison of DB migration scripts and models.

    Allows to check if the DB schema obtained by applying of migration
    scripts is equal to the one produced from models definitions.
    """

    ALEMBIC_CONFIG = alembic_config.Config(
        os.path.join(os.path.dirname(sahara.db.migration.__file__),
                     'alembic.ini')
    )
    ALEMBIC_CONFIG.sahara_config = CONF

    def get_engine(self):
        return self.engine

    def db_sync(self, engine):
        CONF.set_override('connection', str(engine.url), group='database')
        alembic.command.upgrade(self.ALEMBIC_CONFIG, 'head')

    def get_metadata(self):
        return model_base.SaharaBase.metadata
