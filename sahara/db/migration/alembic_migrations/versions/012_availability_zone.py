# -*- coding: utf-8 -*-
# Copyright 2014, Adrien Vergé <adrien.verge@numergy.com>
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

"""add availability_zone field to node groups

Revision ID: 012
Revises: 011
Create Date: 2014-09-08 15:37:00.000000

"""

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('availability_zone', sa.String(length=255)))
    op.add_column('node_groups',
                  sa.Column('availability_zone', sa.String(length=255)))
    op.add_column('templates_relations',
                  sa.Column('availability_zone', sa.String(length=255)))
