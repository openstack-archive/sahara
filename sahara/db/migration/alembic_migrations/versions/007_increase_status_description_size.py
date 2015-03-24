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

"""convert clusters.status_description to LongText

Revision ID: 007
Revises: 006
Create Date: 2014-06-20 22:36:00.783444

"""

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'

from alembic import op

from sahara.db.sqlalchemy import types as st


def upgrade():
    op.alter_column('clusters', 'status_description',
                    type_=st.LongText(), existing_nullable=True,
                    existing_server_default=None)
