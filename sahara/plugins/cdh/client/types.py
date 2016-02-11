# Copyright (c) 2014 Intel Corporation.
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
#
# The contents of this file are mainly copied from cm_api sources,
# released by Cloudera. Codes not used by Sahara CDH plugin are removed.
# You can find the original codes at
#
#     https://github.com/cloudera/cm_api/tree/master/python/src/cm_api
#
# To satisfy the pep8 and python3 tests, we did some changes to the codes.
# We also change some importings to use Sahara inherited classes.

import copy
import datetime
import time

from oslo_serialization import jsonutils as json
from oslo_utils import reflection
import six

from sahara import context
from sahara.i18n import _
from sahara.plugins.cdh import exceptions as ex


class Attr(object):
    """Base Attribute

    Encapsulates information about an attribute in the JSON encoding of the
    object. It identifies properties of the attribute such as whether it's
    read-only, its type, etc.
    """
    DATE_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

    def __init__(self, atype=None, rw=True, is_api_list=False):
        self._atype = atype
        self._is_api_list = is_api_list
        self.rw = rw

    def to_json(self, value, preserve_ro):
        """Returns the JSON encoding of the given attribute value

        If the value has a 'to_json_dict' object, that method is called.
        Otherwise, the following values are returned for each input type:
         - datetime.datetime: string with the API representation of a date.
         - dictionary: if 'atype' is ApiConfig, a list of ApiConfig objects.
         - python list: python list (or ApiList) with JSON encoding of items
         - the raw value otherwise
        """
        if hasattr(value, 'to_json_dict'):
            return value.to_json_dict(preserve_ro)
        elif isinstance(value, dict) and self._atype == ApiConfig:
            return config_to_api_list(value)
        elif isinstance(value, datetime.datetime):
            return value.strftime(self.DATE_FMT)
        elif isinstance(value, list) or isinstance(value, tuple):
            if self._is_api_list:
                return ApiList(value).to_json_dict()
            else:
                return [self.to_json(x, preserve_ro) for x in value]
        else:
            return value

    def from_json(self, resource_root, data):
        """Parses the given JSON value into an appropriate python object

        This means:
         - a datetime.datetime if 'atype' is datetime.datetime
         - a converted config dictionary or config list if 'atype' is ApiConfig
         - if the attr is an API list, an ApiList with instances of 'atype'
         - an instance of 'atype' if it has a 'from_json_dict' method
         - a python list with decoded versions of the member objects if the
           input is a python list.
         - the raw value otherwise
        """
        if data is None:
            return None

        if self._atype == datetime.datetime:
            return datetime.datetime.strptime(data, self.DATE_FMT)
        elif self._atype == ApiConfig:
            # ApiConfig is special. We want a python dictionary for summary
            # views, but an ApiList for full views. Try to detect each case
            # from the JSON data.
            if not data['items']:
                return {}
            first = data['items'][0]
            return json_to_config(data, len(first) == 2)
        elif self._is_api_list:
            return ApiList.from_json_dict(data, resource_root, self._atype)
        elif isinstance(data, list):
            return [self.from_json(resource_root, x) for x in data]
        elif hasattr(self._atype, 'from_json_dict'):
            return self._atype.from_json_dict(data, resource_root)
        else:
            return data


class ROAttr(Attr):
    """Subclass that just defines the attribute as read-only."""
    def __init__(self, atype=None, is_api_list=False):
        Attr.__init__(self, atype=atype, rw=False, is_api_list=is_api_list)


def check_api_version(resource_root, min_version):
    """Check API version

    Checks if the resource_root's API version it at least the given minimum
    version.
    """
    if resource_root.version < min_version:
        raise ex.CMApiVersionError(
            _("API version %(minv)s is required but %(acv)s is in use.")
            % {'minv': min_version, 'acv': resource_root.version})


def call(method, path, ret_type,
         ret_is_list=False, data=None, params=None, api_version=1):
    """Call a resource method

    Generic function for calling a resource method and automatically dealing
    with serialization of parameters and deserialization of return values.

    :param method: method to call (must be bound to a resource;
                                 e.g., "resource_root.get").
    :param path: the full path of the API method to call.
    :param ret_type: return type of the call.
    :param ret_is_list: whether the return type is an ApiList.
    :param data: Optional data to send as payload to the call.
    :param params: Optional query parameters for the call.
    :param api_version: minimum API version for the call.
    """
    check_api_version(method.im_self, api_version)
    if data is not None:
        data = json.dumps(Attr(is_api_list=True).to_json(data, False))
        ret = method(path, data=data, params=params)
    else:
        ret = method(path, params=params)
    if ret_type is None:
        return
    elif ret_is_list:
        return ApiList.from_json_dict(ret, method.im_self, ret_type)
    elif isinstance(ret, list):
        return [ret_type.from_json_dict(x, method.im_self) for x in ret]
    else:
        return ret_type.from_json_dict(ret, method.im_self)


class BaseApiObject(object):
    """The BaseApiObject helps with (de)serialization from/to JSON

    The derived class has two ways of defining custom attributes:
     - Overwriting the '_ATTRIBUTES' field with the attribute dictionary
     - Override the _get_attributes() method, in case static initialization of
       the above field is not possible.

    It's recommended that the _get_attributes() implementation do caching to
    avoid computing the dictionary on every invocation.

    The derived class's constructor must call the base class's init() static
    method. All constructor arguments (aside from self and resource_root) must
    be keywords arguments with default values (typically None), or
    from_json_dict() will not work.
    """

    _ATTRIBUTES = {}
    _WHITELIST = ('_resource_root', '_attributes')

    @classmethod
    def _get_attributes(cls):
        """Get an attribute dictionary

        Returns a map of property names to attr instances (or None for default
        attribute behavior) describing the properties of the object.

        By default, this method will return the class's _ATTRIBUTES field.
        Classes can override this method to do custom initialization of the
        attributes when needed.
        """
        return cls._ATTRIBUTES

    @staticmethod
    def init(obj, resource_root, attrs=None):
        """Wraper of real constructor

        Wraper around the real constructor to avoid issues with the 'self'
        argument. Call like this, from a subclass's constructor:

         - BaseApiObject.init(self, locals())
        """
        # This works around http://bugs.python.org/issue2646
        # We use unicode strings as keys in kwargs.
        str_attrs = {}
        if attrs:
            for k, v in six.iteritems(attrs):
                if k not in ('self', 'resource_root'):
                    str_attrs[k] = v
        BaseApiObject.__init__(obj, resource_root, **str_attrs)

    def __init__(self, resource_root, **attrs):
        """Init method

        Initializes internal state and sets all known writable properties of
        the object to None. Then initializes the properties given in the
        provided attributes dictionary.

        :param resource_root: API resource object.
        :param attrs: optional dictionary of attributes to set. This should
                      only contain r/w attributes.
        """
        self._resource_root = resource_root

        for name, attr in six.iteritems(self._get_attributes()):
            object.__setattr__(self, name, None)
        if attrs:
            self._set_attrs(attrs, from_json=False)

    def _set_attrs(self, attrs, allow_ro=False, from_json=True):
        """Set attributes from dictionary

        Sets all the attributes in the dictionary. Optionally, allows setting
        read-only attributes (e.g. when deserializing from JSON) and skipping
        JSON deserialization of values.
        """
        for k, v in six.iteritems(attrs):
            attr = self._check_attr(k, allow_ro)
            if attr and from_json:
                v = attr.from_json(self._get_resource_root(), v)
            object.__setattr__(self, k, v)

    def __setattr__(self, name, val):
        if name not in BaseApiObject._WHITELIST:
            self._check_attr(name, False)
        object.__setattr__(self, name, val)

    def _check_attr(self, name, allow_ro):
        cls_name = reflection.get_class_name(self, fully_qualified=False)
        if name not in self._get_attributes():
            raise ex.CMApiAttributeError(
                _('Invalid property %(attname)s for class %(classname)s.')
                % {'attname': name, 'classname': cls_name})
        attr = self._get_attributes()[name]
        if not allow_ro and attr and not attr.rw:
            raise ex.CMApiAttributeError(
                _('Attribute %(attname)s of class %(classname)s '
                  'is read only.')
                % {'attname': name, 'classname': cls_name})
        return attr

    def _get_resource_root(self):
        return self._resource_root

    def _update(self, api_obj):
        """Copy state from api_obj to this object."""
        if not isinstance(self, api_obj.__class__):
            raise ex.CMApiValueError(
                _("Class %(class1)s does not derive from %(class2)s; "
                    "cannot update attributes.")
                % {'class1': self.__class__, 'class2': api_obj.__class__})

        for name in self._get_attributes().keys():
            try:
                val = getattr(api_obj, name)
                setattr(self, name, val)
            except AttributeError:
                pass

    def to_json_dict(self, preserve_ro=False):
        dic = {}
        for name, attr in six.iteritems(self._get_attributes()):
            if not preserve_ro and attr and not attr.rw:
                continue
            try:
                value = getattr(self, name)
                if value is not None:
                    if attr:
                        dic[name] = attr.to_json(value, preserve_ro)
                    else:
                        dic[name] = value
            except AttributeError:
                pass
        return dic

    def __str__(self):
        """Give a printable format of an attribute

        Default implementation of __str__. Uses the type name and the first
        attribute retrieved from the attribute map to create the string.
        """
        cls_name = reflection.get_class_name(self, fully_qualified=False)
        name = list(self._get_attributes().keys())[0]
        value = getattr(self, name, None)
        return "<%s>: %s = %s" % (cls_name, name, value)

    @classmethod
    def from_json_dict(cls, dic, resource_root):
        obj = cls(resource_root)
        obj._set_attrs(dic, allow_ro=True)
        return obj


class BaseApiResource(BaseApiObject):
    """Base ApiResource

    A specialization of BaseApiObject that provides some utility methods for
    resources. This class allows easier serialization / deserialization of
    parameters and return values.
    """

    def _api_version(self):
        """Get API version

        Returns the minimum API version for this resource. Defaults to 1.
        """
        return 1

    def _path(self):
        """Get resource path

        Returns the path to the resource.

        e.g., for a service 'foo' in cluster 'bar', this should return
        '/clusters/bar/services/foo'.
        """
        raise NotImplementedError

    def _require_min_api_version(self, version):
        """Check mininum verson requirement

        Raise an exception if the version of the api is less than the given
        version.

        :param version: The minimum required version.
        """
        actual_version = self._get_resource_root().version
        version = max(version, self._api_version())
        if actual_version < version:
            raise ex.CMApiVersionError(
                _("API version %(minv)s is required but %(acv)s is in use.")
                % {'minv': version, 'acv': actual_version})

    def _cmd(self, command, data=None, params=None, api_version=1):
        """Invoke a command on the resource

        Invokes a command on the resource. Commands are expected to be under
        the "commands/" sub-resource.
        """
        return self._post("commands/" + command, ApiCommand,
                          data=data, params=params, api_version=api_version)

    def _get_config(self, rel_path, view, api_version=1):
        """Get resource configurations

        Retrieves an ApiConfig list from the given relative path.
        """
        self._require_min_api_version(api_version)
        params = dict(view=view) if view else None
        resp = self._get_resource_root().get(self._path() + '/' + rel_path,
                                             params=params)
        return json_to_config(resp, view == 'full')

    def _update_config(self, rel_path, config, api_version=1):
        self._require_min_api_version(api_version)
        resp = self._get_resource_root().put(self._path() + '/' + rel_path,
                                             data=config_to_json(config))
        return json_to_config(resp, False)

    def _delete(self, rel_path, ret_type, ret_is_list=False, params=None,
                api_version=1):
        return self._call('delete', rel_path, ret_type, ret_is_list, None,
                          params, api_version)

    def _get(self, rel_path, ret_type, ret_is_list=False, params=None,
             api_version=1):
        return self._call('get', rel_path, ret_type, ret_is_list, None,
                          params, api_version)

    def _post(self, rel_path, ret_type, ret_is_list=False, data=None,
              params=None, api_version=1):
        return self._call('post', rel_path, ret_type, ret_is_list, data,
                          params, api_version)

    def _put(self, rel_path, ret_type, ret_is_list=False, data=None,
             params=None, api_version=1):
        return self._call('put', rel_path, ret_type, ret_is_list, data,
                          params, api_version)

    def _call(self, method, rel_path, ret_type, ret_is_list=False, data=None,
              params=None, api_version=1):
        path = self._path()
        if rel_path:
            path += '/' + rel_path
        return call(getattr(self._get_resource_root(), method),
                    path,
                    ret_type,
                    ret_is_list,
                    data,
                    params,
                    api_version)


class ApiList(BaseApiObject):
    """A list of some api object"""
    LIST_KEY = "items"

    def __init__(self, objects, resource_root=None, **attrs):
        BaseApiObject.__init__(self, resource_root, **attrs)
        # Bypass checks in BaseApiObject.__setattr__
        object.__setattr__(self, 'objects', objects)

    def __str__(self):
        return ("<ApiList>(%d): [%s]" % (len(self.objects),
                ", ".join([str(item) for item in self.objects])))

    def to_json_dict(self, preserve_ro=False):
        ret = BaseApiObject.to_json_dict(self, preserve_ro)
        attr = Attr()
        ret[ApiList.LIST_KEY] = [attr.to_json(x, preserve_ro)
                                 for x in self.objects]
        return ret

    def __len__(self):
        return self.objects.__len__()

    def __iter__(self):
        return self.objects.__iter__()

    def __getitem__(self, i):
        return self.objects.__getitem__(i)

    def __getslice__(self, i, j):
        return self.objects.__getslice__(i, j)

    @classmethod
    def from_json_dict(cls, dic, resource_root, member_cls=None):
        if not member_cls:
            member_cls = cls._MEMBER_CLASS
        attr = Attr(atype=member_cls)
        items = []
        if ApiList.LIST_KEY in dic:
            items = [attr.from_json(resource_root, x)
                     for x in dic[ApiList.LIST_KEY]]
        ret = cls(items)
        # If the class declares custom attributes, populate them based on the
        # input dict. The check avoids extra overhead for the common case,
        # where we just have a plain list. _set_attrs() also does not
        # understand the "items" attribute, so it can't be in the input data.
        if cls._ATTRIBUTES:
            if ApiList.LIST_KEY in dic:
                dic = copy.copy(dic)
                del dic[ApiList.LIST_KEY]
            ret._set_attrs(dic, allow_ro=True)
        return ret


class ApiHostRef(BaseApiObject):
    _ATTRIBUTES = {
        'hostId': None,
    }

    def __init__(self, resource_root, hostId=None):
        BaseApiObject.init(self, resource_root, locals())

    def __str__(self):
        return "<ApiHostRef>: %s" % (self.hostId)


class ApiServiceRef(BaseApiObject):
    _ATTRIBUTES = {
        'clusterName': None,
        'serviceName': None,
        'peerName': None,
    }

    def __init__(self, resource_root, serviceName=None, clusterName=None,
                 peerName=None):
        BaseApiObject.init(self, resource_root, locals())


class ApiClusterRef(BaseApiObject):
    _ATTRIBUTES = {
        'clusterName': None,
    }

    def __init__(self, resource_root, clusterName=None):
        BaseApiObject.init(self, resource_root, locals())


class ApiRoleRef(BaseApiObject):
    _ATTRIBUTES = {
        'clusterName': None,
        'serviceName': None,
        'roleName': None,
    }

    def __init__(self, resource_root, serviceName=None, roleName=None,
                 clusterName=None):
        BaseApiObject.init(self, resource_root, locals())


class ApiRoleConfigGroupRef(BaseApiObject):
    _ATTRIBUTES = {
        'roleConfigGroupName': None,
    }

    def __init__(self, resource_root, roleConfigGroupName=None):
        BaseApiObject.init(self, resource_root, locals())


class ApiCommand(BaseApiObject):
    SYNCHRONOUS_COMMAND_ID = -1

    @classmethod
    def _get_attributes(cls):
        if not ('_ATTRIBUTES' in cls.__dict__):
            cls._ATTRIBUTES = {
                'id': ROAttr(),
                'name': ROAttr(),
                'startTime': ROAttr(datetime.datetime),
                'endTime': ROAttr(datetime.datetime),
                'active': ROAttr(),
                'success': ROAttr(),
                'resultMessage': ROAttr(),
                'clusterRef': ROAttr(ApiClusterRef),
                'serviceRef': ROAttr(ApiServiceRef),
                'roleRef': ROAttr(ApiRoleRef),
                'hostRef': ROAttr(ApiHostRef),
                'children': ROAttr(ApiCommand, is_api_list=True),
                'parent': ROAttr(ApiCommand),
                'resultDataUrl': ROAttr(),
            }
        return cls._ATTRIBUTES

    def __str__(self):
        return ("<ApiCommand>: '%s' (id: %s; active: %s; success: %s)"
                % (self.name, self.id, self.active, self.success))

    def _path(self):
        return '/commands/%d' % self.id

    def fetch(self):
        """Retrieve updated data about the command from the server

        :return: A new ApiCommand object.
        """
        if self.id == ApiCommand.SYNCHRONOUS_COMMAND_ID:
            return self

        resp = self._get_resource_root().get(self._path())
        return ApiCommand.from_json_dict(resp, self._get_resource_root())

    def wait(self, timeout=None):
        """Wait for command to finish

        :param timeout: (Optional) Max amount of time (in seconds) to wait.
                        Wait forever by default.
        :return: The final ApiCommand object, containing the last known state.
                 The command may still be running in case of timeout.
        """
        if self.id == ApiCommand.SYNCHRONOUS_COMMAND_ID:
            return self

        SLEEP_SEC = 5

        if timeout is None:
            deadline = None
        else:
            deadline = time.time() + timeout

        while True:
            cmd = self.fetch()
            if not cmd.active:
                return cmd

            if deadline is not None:
                now = time.time()
                if deadline < now:
                    return cmd
                else:
                    context.sleep(min(SLEEP_SEC, deadline - now))
            else:
                context.sleep(SLEEP_SEC)

    def abort(self):
        """Abort a running command

        :return: A new ApiCommand object with the updated information.
        """
        if self.id == ApiCommand.SYNCHRONOUS_COMMAND_ID:
            return self

        path = self._path() + '/abort'
        resp = self._get_resource_root().post(path)
        return ApiCommand.from_json_dict(resp, self._get_resource_root())


class ApiBulkCommandList(ApiList):
    _ATTRIBUTES = {
        'errors': ROAttr(),
    }
    _MEMBER_CLASS = ApiCommand


#
# Configuration helpers.
#
class ApiConfig(BaseApiObject):
    _ATTRIBUTES = {
        'name': None,
        'value': None,
        'required': ROAttr(),
        'default': ROAttr(),
        'displayName': ROAttr(),
        'description': ROAttr(),
        'relatedName': ROAttr(),
        'validationState': ROAttr(),
        'validationMessage': ROAttr(),
    }

    def __init__(self, resource_root, name=None, value=None):
        BaseApiObject.init(self, resource_root, locals())

    def __str__(self):
        return "<ApiConfig>: %s = %s" % (self.name, self.value)


def config_to_api_list(dic):
    """Convert a python dictionary into an ApiConfig list

    Converts a python dictionary into a list containing the proper
    ApiConfig encoding for configuration data.

    :param dic: Key-value pairs to convert.
    :return: JSON dictionary of an ApiConfig list (*not* an ApiList).
    """
    config = []
    for k, v in six.iteritems(dic):
        config.append({'name': k, 'value': v})
    return {ApiList.LIST_KEY: config}


def config_to_json(dic):
    """Converts a python dictionary into a JSON payload

    The payload matches the expected "apiConfig list" type used to update
    configuration parameters using the API.

    :param dic: Key-value pairs to convert.
    :return: String with the JSON-encoded data.
    """
    return json.dumps(config_to_api_list(dic))


def json_to_config(dic, full=False):
    """Converts a JSON-decoded config dictionary to a python dictionary

    When materializing the full view, the values in the dictionary will be
    instances of ApiConfig, instead of strings.

    :param dic: JSON-decoded config dictionary.
    :param full: Whether to materialize the full view of the config data.
    :return: Python dictionary with config data.
    """
    config = {}
    for entry in dic['items']:
        k = entry['name']
        if full:
            config[k] = ApiConfig.from_json_dict(entry, None)
        else:
            config[k] = entry.get('value')
    return config
