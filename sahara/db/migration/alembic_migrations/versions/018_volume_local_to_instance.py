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

"""add volume_local_to_instance flag

Revision ID: 018
Revises: 017
Create Date: 2015-03-03 14:35:43.625429

"""

# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('volume_local_to_instance', sa.Boolean()))
    op.add_column('node_groups',
                  sa.Column('volume_local_to_instance', sa.Boolean()))
    op.add_column('templates_relations',
                  sa.Column('volume_local_to_instance', sa.Boolean()))
