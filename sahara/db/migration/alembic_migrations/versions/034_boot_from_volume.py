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

"""Add boot_from_volumes field for node_groups and related classes

Revision ID: 034
Revises: 033
Create Date: 2018-06-06 17:36:04.749264

"""

# revision identifiers, used by Alembic.
revision = '034'
down_revision = '033'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('boot_from_volume', sa.Boolean(), nullable=False))

    op.add_column('node_groups',
                  sa.Column('boot_from_volume', sa.Boolean(), nullable=False))

    op.add_column('templates_relations',
                  sa.Column('boot_from_volume', sa.Boolean(), nullable=False))
