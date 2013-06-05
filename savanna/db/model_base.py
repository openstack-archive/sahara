# Copyright (c) 2013 Mirantis Inc.
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

import re

import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import orm

from savanna.openstack.common import timeutils
from savanna.openstack.common import uuidutils
from savanna.utils import resources
from savanna.utils import sqlatypes as st


class _SavannaBase(resources.BaseResource):
    """Base class for all Savanna Models."""

    created = sa.Column(sa.DateTime, default=timeutils.utcnow,
                        nullable=False)
    updated = sa.Column(sa.DateTime, default=timeutils.utcnow,
                        nullable=False, onupdate=timeutils.utcnow)

    __protected_attributes__ = ["created", "updated"]

    @declarative.declared_attr
    def __tablename__(cls):
        # Table name is equals to the class name
        return cls.__name__

    @property
    def __resource_name__(self):
        # convert CamelCase class name to camel_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.__class__.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __iter__(self):
        self._i = iter(orm.object_mapper(self).columns)
        return self

    def next(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.iteritems():
            setattr(self, k, v)

    def iteritems(self):
        """Make the model object behave like a dict.

        Includes attributes from joins.
        """
        local = dict(self)
        joined = dict([(k, v) for k, v in self.__dict__.iteritems()
                       if not k[0] == '_'])
        local.update(joined)
        return local.iteritems()

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def __repr__(self):
        """sqlalchemy based automatic __repr__ method."""
        items = ['%s=%r' % (col.name, getattr(self, col.name))
                 for col in self.__table__.columns]
        return "<%s.%s[object at %x] {%s}>" % (self.__class__.__module__,
                                               self.__class__.__name__,
                                               id(self), ', '.join(items))

    def to_dict(self):
        """sqlalchemy based automatic to_dict method."""
        d = {}
        for col in self.__table__.columns:
            if self._filter_field(col.name):
                continue
            d[col.name] = getattr(self, col.name)
        return d


SavannaBase = declarative.declarative_base(cls=_SavannaBase)


def _generate_unicode_uuid():
    return unicode(uuidutils.generate_uuid())


class IdMixin(object):
    """Id mixin, add to subclasses that have an id."""

    id = sa.Column(sa.String(36),
                   primary_key=True,
                   default=_generate_unicode_uuid)


class TenantMixin(object):
    """Tenant mixin, add to subclasses that have a tenant."""

    __filter_cols__ = ['tenant_id']

    tenant_id = sa.Column(sa.String(36))


class PluginSpecificMixin(object):
    """Plugin specific info mixin, add to subclass that plugin specific."""

    plugin_name = sa.Column(sa.String(80), nullable=False)
    hadoop_version = sa.Column(sa.String(80), nullable=False)


class ExtraMixin(object):
    """Extra info mixin, add to subclass that stores extra data w/o schema."""

    __filter_cols__ = ['extra']

    extra = sa.Column(st.JsonDictType())
