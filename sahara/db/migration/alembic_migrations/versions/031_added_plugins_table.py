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

"""added_plugins_table

Revision ID: 031
Revises: 030
Create Date: 2016-06-21 13:32:40.151321

"""

from alembic import op
import sqlalchemy as sa

from sahara.db.sqlalchemy import types as st

# revision identifiers, used by Alembic.
revision = '031'
down_revision = '030'


def upgrade():
    op.create_table(
        'plugin_data',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=15), nullable=False),
        sa.Column('plugin_labels', st.JsonEncoded(), nullable=True),
        sa.Column('version_labels', st.JsonEncoded(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'tenant_id')
    )
