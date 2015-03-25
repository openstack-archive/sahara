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

"""add security_groups field to node groups

Revision ID: 008
Revises: 007
Create Date: 2014-07-15 14:31:49.685689

"""

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'

from alembic import op
import sqlalchemy as sa

from sahara.db.sqlalchemy import types as st


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('security_groups', st.JsonEncoded()))
    op.add_column('node_groups',
                  sa.Column('security_groups', st.JsonEncoded()))
    op.add_column('templates_relations',
                  sa.Column('security_groups', st.JsonEncoded()))
