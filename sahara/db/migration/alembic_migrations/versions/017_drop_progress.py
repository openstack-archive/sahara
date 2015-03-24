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

"""drop progress in JobExecution

Revision ID: 017
Revises: 016
Create Date: 2015-02-25 09:23:04.390388

"""

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'

from alembic import op


def upgrade():
    op.drop_column('job_executions', 'progress')
