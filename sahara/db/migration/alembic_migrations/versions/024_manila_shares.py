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

"""manila_shares

Revision ID: 024
Revises: 023
Create Date: 2015-07-20 14:51:20.275823

"""

# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'

from alembic import op
import sqlalchemy as sa

from sahara.db.sqlalchemy import types as st


MYSQL_ENGINE = 'InnoDB'
MYSQL_CHARSET = 'utf8'


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('shares', st.JsonEncoded()))
    op.add_column('node_groups',
                  sa.Column('shares', st.JsonEncoded()))
    op.add_column('templates_relations',
                  sa.Column('shares', st.JsonEncoded()))
    op.add_column('clusters',
                  sa.Column('shares', st.JsonEncoded()))
    op.add_column('cluster_templates',
                  sa.Column('shares', st.JsonEncoded()))
