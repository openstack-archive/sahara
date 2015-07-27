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

"""Rename oozie_job_id

Revision ID: 027
Revises: 026
Create Date: 2015-07-27 14:31:02.413053

"""

# revision identifiers, used by Alembic.
revision = '027'
down_revision = '026'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('job_executions', 'oozie_job_id',
                    new_column_name="engine_job_id",
                    type_=sa.String(length=100))
