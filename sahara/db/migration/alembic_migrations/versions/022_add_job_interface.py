# Copyright 2015 Red Hat, Inc.
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

"""add_job_interface

Revision ID: 022
Revises: 021
Create Date: 2015-01-27 15:53:22.128263

"""

# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021'

from alembic import op
import sqlalchemy as sa

MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.create_table('job_interface_arguments',
                    sa.Column('created_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('updated_at', sa.DateTime(),
                              nullable=True),
                    sa.Column('id', sa.String(length=36),
                              nullable=False),
                    sa.Column('job_id', sa.String(length=36),
                              nullable=False),
                    sa.Column('tenant_id', sa.String(length=36),
                              nullable=True),
                    sa.Column('name', sa.String(80),
                              nullable=False),
                    sa.Column('description', sa.Text()),
                    sa.Column('mapping_type', sa.String(80),
                              nullable=False),
                    sa.Column('location', sa.Text(),
                              nullable=False),
                    sa.Column('value_type', sa.String(80),
                              nullable=False),
                    sa.Column('required', sa.Boolean(),
                              nullable=False),
                    sa.Column('order', sa.SmallInteger(),
                              nullable=False),
                    sa.Column('default', sa.Text()),
                    sa.ForeignKeyConstraint(['job_id'],
                                            ['jobs.id']),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('job_id', 'order'),
                    sa.UniqueConstraint('job_id', 'name'),
                    mysql_engine=MYSQL_ENGINE,
                    mysql_charset=MYSQL_CHARSET)
