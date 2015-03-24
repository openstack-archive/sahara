# Copyright 2014 OpenStack Foundation.
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

"""add_events_objects

Revision ID: 015
Revises: 014
Create Date: 2014-11-07 15:20:21.806128

"""

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'

from alembic import op
import sqlalchemy as sa

MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.create_table('cluster_provision_steps',
                    sa.Column('created_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('updated_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('id', sa.String(length=36),
                              nullable=False),
                    sa.Column('cluster_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('tenant_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('step_name', sa.String(length=80),
                              nullable=True),
                    sa.Column('step_type', sa.String(length=36),
                              nullable=True),
                    sa.Column('completed', sa.Integer(),
                              nullable=True),
                    sa.Column('total', sa.Integer(),
                              nullable=True),
                    sa.Column('successful', sa.Boolean(),
                              nullable=True),
                    sa.Column('started_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('completed_at', sa.DateTime(),
                              nullable=True),
                    sa.ForeignKeyConstraint(['cluster_id'],
                                            ['clusters.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id', 'cluster_id'),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)

    op.create_table('cluster_events',
                    sa.Column('created_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('updated_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('id', sa.String(length=36),
                              nullable=False),
                    sa.Column('node_group_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('instance_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('instance_name', sa.String(length=80),
                              nullable=True),
                    sa.Column('event_info', sa.Text(),
                              nullable=True),
                    sa.Column('successful', sa.Boolean(),
                              nullable=False),
                    sa.Column('step_id', sa.String(length=36),
                              nullable=True),
                    sa.ForeignKeyConstraint(
                        ['step_id'],
                        ['cluster_provision_steps.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id', 'step_id'),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)
