# Copyright 2019 OpenStack Foundation.
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

"""boot from volume enhancements

Revision ID: 035
Revises: 034
Create Date: 2019-01-07 19:55:54.025736

"""

# revision identifiers, used by Alembic.
revision = '035'
down_revision = '034'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('node_group_templates',
                  sa.Column('boot_volume_availability_zone',
                            sa.String(length=255),
                            nullable=True))
    op.add_column('node_group_templates',
                  sa.Column('boot_volume_local_to_instance',
                            sa.Boolean(),
                            nullable=True))
    op.add_column('node_group_templates',
                  sa.Column('boot_volume_type',
                            sa.String(length=255),
                            nullable=True))

    op.add_column('node_groups',
                  sa.Column('boot_volume_availability_zone',
                            sa.String(length=255),
                            nullable=True))
    op.add_column('node_groups',
                  sa.Column('boot_volume_local_to_instance',
                            sa.Boolean(),
                            nullable=True))
    op.add_column('node_groups',
                  sa.Column('boot_volume_type',
                            sa.String(length=255),
                            nullable=True))

    op.add_column('templates_relations',
                  sa.Column('boot_volume_availability_zone',
                            sa.String(length=255),
                            nullable=True))
    op.add_column('templates_relations',
                  sa.Column('boot_volume_local_to_instance',
                            sa.Boolean(),
                            nullable=True))
    op.add_column('templates_relations',
                  sa.Column('boot_volume_type',
                            sa.String(length=255),
                            nullable=True))
