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

"""032_add_domain_name

Revision ID: 032
Revises: 031
Create Date: 2016-07-21 13:33:33.674853

"""

# revision identifiers, used by Alembic.
revision = '032'
down_revision = '031'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('cluster_templates', sa.Column(
        'domain_name', sa.String(length=255), nullable=True))
    op.add_column('clusters', sa.Column(
        'domain_name', sa.String(length=255), nullable=True))
    op.add_column('instances', sa.Column(
        'dns_hostname', sa.String(length=255), nullable=True))
