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

"""remove redandunt progress ops

Revision ID: 020
Revises: 019
Create Date: 2015-02-26 15:01:41.015076

"""

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'

from alembic import op


def upgrade():
    op.drop_column('cluster_provision_steps', 'completed_at')
    op.drop_column('cluster_provision_steps', 'completed')
    op.drop_column('cluster_provision_steps', 'started_at')
