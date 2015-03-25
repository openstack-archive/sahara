# Copyright 2015 OpenStack Foundation.
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

"""Add is_default field for cluster and node_group templates

Revision ID: 019
Revises: 018
Create Date: 2015-03-02 14:32:04.415021

"""

# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('cluster_templates',
                  sa.Column('is_default', sa.Boolean(), nullable=True))
    op.add_column('node_group_templates',
                  sa.Column('is_default', sa.Boolean(), nullable=True))
