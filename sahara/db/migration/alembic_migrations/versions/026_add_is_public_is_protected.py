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

"""add is_public and is_protected flags

Revision ID: 026
Revises: 025
Create Date: 2015-06-24 12:41:52.571258

"""

# revision identifiers, used by Alembic.
revision = '026'
down_revision = '025'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('clusters',
                  sa.Column('is_public', sa.Boolean()),)
    op.add_column('cluster_templates',
                  sa.Column('is_public', sa.Boolean()))
    op.add_column('node_group_templates',
                  sa.Column('is_public', sa.Boolean()))
    op.add_column('data_sources',
                  sa.Column('is_public', sa.Boolean()))
    op.add_column('job_executions',
                  sa.Column('is_public', sa.Boolean()))
    op.add_column('jobs',
                  sa.Column('is_public', sa.Boolean()))
    op.add_column('job_binary_internal',
                  sa.Column('is_public', sa.Boolean()))
    op.add_column('job_binaries',
                  sa.Column('is_public', sa.Boolean()))

    op.add_column('clusters',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('cluster_templates',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('node_group_templates',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('data_sources',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('job_executions',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('jobs',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('job_binary_internal',
                  sa.Column('is_protected', sa.Boolean()))
    op.add_column('job_binaries',
                  sa.Column('is_protected', sa.Boolean()))
