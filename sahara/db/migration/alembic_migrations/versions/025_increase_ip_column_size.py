# Copyright 2015 Telles Nobrega
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

"""Increase internal_ip and management_ip column size to work with IPv6

Revision ID: 025
Revises: 024
Create Date: 2015-07-17 09:58:22.128263

"""

# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('instances', 'internal_ip', type_=sa.String(45),
                    nullable=True)
    op.alter_column('instances', 'management_ip', type_=sa.String(45),
                    nullable=True)
