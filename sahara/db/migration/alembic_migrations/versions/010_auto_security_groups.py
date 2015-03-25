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

"""add auto_security_groups flag to node group

Revision ID: 010
Revises: 009
Create Date: 2014-07-21 14:31:49.685689

"""

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'

from alembic import op
import sqlalchemy as sa

from sahara.db.sqlalchemy import types as st


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('auto_security_group', sa.Boolean()))
    op.add_column('node_groups',
                  sa.Column('auto_security_group', sa.Boolean()))
    op.add_column('templates_relations',
                  sa.Column('auto_security_group', sa.Boolean()))
    op.add_column('node_groups',
                  sa.Column('open_ports', st.JsonEncoded()))
