# Copyright 2016 OpenStack Foundation.
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

"""health-check

Revision ID: 029
Revises: 028
Create Date: 2016-01-26 16:11:46.008367

"""

# revision identifiers, used by Alembic.
revision = '030'
down_revision = '029'

from alembic import op
import sqlalchemy as sa


MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.create_table(
        'cluster_verifications',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('cluster_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=15), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['clusters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'cluster_id'),
        mysql_engine=MYSQL_ENGINE,
        mysql_charset=MYSQL_CHARSET)
    op.create_table(
        'cluster_health_checks',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('verification_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=15), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('name', sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(
            ['verification_id'], ['cluster_verifications.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'verification_id'),
        mysql_engine=MYSQL_ENGINE,
        mysql_charset=MYSQL_CHARSET)
