# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# Only (de)serialization utils hasn't been removed to decrease requirements
# number.

"""Utility methods for working with WSGI servers."""

import datetime
import errno
import os
import signal
from xml.dom import minidom
from xml.parsers import expat
from xml import sax
from xml.sax import expatreader

import eventlet
from eventlet import wsgi
from oslo_config import cfg
from oslo_log import log as logging
from oslo_log import loggers
from oslo_serialization import jsonutils
import six

from sahara import exceptions
from sahara.i18n import _
from sahara.i18n import _LE
from sahara.i18n import _LI
from sahara.openstack.common import sslutils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class ProtectedExpatParser(expatreader.ExpatParser):
    """An expat parser which disables DTD's and entities by default."""

    def __init__(self, forbid_dtd=True, forbid_entities=True,
                 *args, **kwargs):
        # Python 2.x old style class
        expatreader.ExpatParser.__init__(self, *args, **kwargs)
        self.forbid_dtd = forbid_dtd
        self.forbid_entities = forbid_entities

    def start_doctype_decl(self, name, sysid, pubid, has_internal_subset):
        raise ValueError("Inline DTD forbidden")

    def entity_decl(self, entityName, is_parameter_entity, value, base,
                    systemId, publicId, notationName):
        raise ValueError("<!ENTITY> entity declaration forbidden")

    def unparsed_entity_decl(self, name, base, sysid, pubid, notation_name):
        # expat 1.2
        raise ValueError("<!ENTITY> unparsed entity forbidden")

    def external_entity_ref(self, context, base, systemId, publicId):
        raise ValueError("<!ENTITY> external entity forbidden")

    def notation_decl(self, name, base, sysid, pubid):
        raise ValueError("<!ENTITY> notation forbidden")

    def reset(self):
        expatreader.ExpatParser.reset(self)
        if self.forbid_dtd:
            self._parser.StartDoctypeDeclHandler = self.start_doctype_decl
            self._parser.EndDoctypeDeclHandler = None
        if self.forbid_entities:
            self._parser.EntityDeclHandler = self.entity_decl
            self._parser.UnparsedEntityDeclHandler = self.unparsed_entity_decl
            self._parser.ExternalEntityRefHandler = self.external_entity_ref
            self._parser.NotationDeclHandler = self.notation_decl
            try:
                self._parser.SkippedEntityHandler = None
            except AttributeError:
                # some pyexpat versions do not support SkippedEntity
                pass


def safe_minidom_parse_string(xml_string):
    """Parse an XML string using minidom safely.

    """
    try:
        return minidom.parseString(xml_string, parser=ProtectedExpatParser())
    except sax.SAXParseException:
        raise expat.ExpatError()


class ActionDispatcher(object):
    """Maps method name to local methods through action name."""

    def dispatch(self, *args, **kwargs):
        """Find and call local method."""
        action = kwargs.pop('action', 'default')
        action_method = getattr(self, str(action), self.default)
        return action_method(*args, **kwargs)

    def default(self, data):
        raise NotImplementedError()


class DictSerializer(ActionDispatcher):
    """Default request body serialization."""

    def serialize(self, data, action='default'):
        return self.dispatch(data, action=action)

    def default(self, data):
        return ""


class JSONDictSerializer(DictSerializer):
    """Default JSON request body serialization."""

    def default(self, data):
        def sanitizer(obj):
            if isinstance(obj, datetime.datetime):
                _dtime = obj - datetime.timedelta(microseconds=obj.microsecond)
                return _dtime.isoformat()
            return unicode(obj)
        return jsonutils.dumps(data, default=sanitizer)


class XMLDictSerializer(DictSerializer):

    def __init__(self, metadata=None, xmlns=None):
        """:param metadata: information needed to deserialize xml

        into a dictionary.
        :param xmlns: XML namespace to include with serialized xml
        """
        super(XMLDictSerializer, self).__init__()
        self.metadata = metadata or {}
        self.xmlns = xmlns

    def default(self, data):
        # We expect data to contain a single key which is the XML root.
        root_key = data.keys()[0]
        doc = minidom.Document()
        node = self._to_xml_node(doc, self.metadata, root_key, data[root_key])

        return self.to_xml_string(node)

    def to_xml_string(self, node, has_atom=False):
        self._add_xmlns(node, has_atom)
        return node.toprettyxml(indent='    ', encoding='UTF-8')

    # NOTE (ameade): the has_atom should be removed after all of the
    # xml serializers and view builders have been updated to the current
    # spec that required all responses include the xmlns:atom, the has_atom
    # flag is to prevent current tests from breaking
    def _add_xmlns(self, node, has_atom=False):
        if self.xmlns is not None:
            node.setAttribute('xmlns', self.xmlns)
        if has_atom:
            node.setAttribute('xmlns:atom', "http://www.w3.org/2005/Atom")

    def _to_xml_node(self, doc, metadata, nodename, data):
        """Recursive method to convert data members to XML nodes."""
        result = doc.createElement(nodename)

        # Set the xml namespace if one is specified
        # TODO(justinsb): We could also use prefixes on the keys
        xmlns = metadata.get('xmlns', None)
        if xmlns:
            result.setAttribute('xmlns', xmlns)

        # TODO(bcwaldon): accomplish this without a type-check
        if type(data) is list:
            collections = metadata.get('list_collections', {})
            if nodename in collections:
                metadata = collections[nodename]
                for item in data:
                    node = doc.createElement(metadata['item_name'])
                    node.setAttribute(metadata['item_key'], str(item))
                    result.appendChild(node)
                return result
            singular = metadata.get('plurals', {}).get(nodename, None)
            if singular is None:
                if nodename.endswith('s'):
                    singular = nodename[:-1]
                else:
                    singular = 'item'
            for item in data:
                node = self._to_xml_node(doc, metadata, singular, item)
                result.appendChild(node)
        # TODO(bcwaldon): accomplish this without a type-check
        elif type(data) is dict:
            collections = metadata.get('dict_collections', {})
            if nodename in collections:
                metadata = collections[nodename]
                for k, v in data.items():
                    node = doc.createElement(metadata['item_name'])
                    node.setAttribute(metadata['item_key'], str(k))
                    text = doc.createTextNode(str(v))
                    node.appendChild(text)
                    result.appendChild(node)
                return result
            attrs = metadata.get('attributes', {}).get(nodename, {})
            for k, v in data.items():
                if k in attrs:
                    result.setAttribute(k, str(v))
                else:
                    node = self._to_xml_node(doc, metadata, k, v)
                    result.appendChild(node)
        else:
            # Type is atom
            node = doc.createTextNode(str(data))
            result.appendChild(node)
        return result

    def _create_link_nodes(self, xml_doc, links):
        link_nodes = []
        for link in links:
            link_node = xml_doc.createElement('atom:link')
            link_node.setAttribute('rel', link['rel'])
            link_node.setAttribute('href', link['href'])
            if 'type' in link:
                link_node.setAttribute('type', link['type'])
            link_nodes.append(link_node)
        return link_nodes


class TextDeserializer(ActionDispatcher):
    """Default request body deserialization."""

    def deserialize(self, datastring, action='default'):
        return self.dispatch(datastring, action=action)

    def default(self, datastring):
        return {}


class JSONDeserializer(TextDeserializer):

    def _from_json(self, datastring):
        try:
            return jsonutils.loads(datastring)
        except ValueError:
            msg = _("cannot understand JSON")
            raise exceptions.MalformedRequestBody(msg)

    def default(self, datastring):
        return {'body': self._from_json(datastring)}


class XMLDeserializer(TextDeserializer):

    def __init__(self, metadata=None):
        """:param metadata: information needed to

        deserialize xml into a dictionary.
        """
        super(XMLDeserializer, self).__init__()
        self.metadata = metadata or {}

    def _from_xml(self, datastring):
        plurals = set(self.metadata.get('plurals', {}))

        try:
            node = safe_minidom_parse_string(datastring).childNodes[0]
            return {node.nodeName: self._from_xml_node(node, plurals)}
        except expat.ExpatError:
            msg = _("cannot understand XML")
            raise exceptions.MalformedRequestBody(msg)

    def _from_xml_node(self, node, listnames):
        """Convert a minidom node to a simple Python type.

        :param listnames: list of XML node names whose subnodes should
                          be considered list items.

        """

        if len(node.childNodes) == 1 and node.childNodes[0].nodeType == 3:
            return node.childNodes[0].nodeValue
        elif node.nodeName in listnames:
            return [self._from_xml_node(n, listnames) for n in node.childNodes]
        else:
            result = dict()
            for attr, val in six.iteritems(node.attributes):
                result[attr] = val.nodeValue
            for child in node.childNodes:
                if child.nodeType != node.TEXT_NODE:
                    result[child.nodeName] = self._from_xml_node(child,
                                                                 listnames)
            return result

    def find_first_child_named(self, parent, name):
        """Search a nodes children for the first child with a given name."""
        for node in parent.childNodes:
            if node.nodeName == name:
                return node
        return None

    def find_children_named(self, parent, name):
        """Return all of a nodes children who have the given name."""
        for node in parent.childNodes:
            if node.nodeName == name:
                yield node

    def extract_text(self, node):
        """Get the text field contained by the given node."""
        if len(node.childNodes) == 1:
            child = node.childNodes[0]
            if child.nodeType == child.TEXT_NODE:
                return child.nodeValue
        return ""

    def default(self, datastring):
        return {'body': self._from_xml(datastring)}


class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, threads=500):
        self.threads = threads
        self.children = []
        self.running = True

    def start(self, application):
        """Run a WSGI server with the given application.

        :param application: The application to run in the WSGI server
        """
        def kill_children(*args):
            """Kills the entire process group."""
            LOG.error(_LE('SIGTERM received'))
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            self.running = False
            os.killpg(0, signal.SIGTERM)

        def hup(*args):
            """Shuts down the server(s).

            Shuts down the server(s), but allows running requests to complete
            """
            LOG.error(_LE('SIGHUP received'))
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            os.killpg(0, signal.SIGHUP)
            signal.signal(signal.SIGHUP, hup)

        self.application = application
        self.sock = eventlet.listen((CONF.host, CONF.port), backlog=500)
        if sslutils.is_enabled():
            LOG.info(_LI("Using HTTPS for port %s"), CONF.port)
            self.sock = sslutils.wrap(self.sock)

        if CONF.api_workers == 0:
            # Useful for profiling, test, debug etc.
            self.pool = eventlet.GreenPool(size=self.threads)
            self.pool.spawn_n(self._single_run, application, self.sock)
            return

        LOG.debug("Starting %d workers", CONF.api_workers)
        signal.signal(signal.SIGTERM, kill_children)
        signal.signal(signal.SIGHUP, hup)
        while len(self.children) < CONF.api_workers:
            self.run_child()

    def wait_on_children(self):
        while self.running:
            try:
                pid, status = os.wait()
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    LOG.error(_LE('Removing dead child %s'), pid)
                    self.children.remove(pid)
                    self.run_child()
            except OSError as err:
                if err.errno not in (errno.EINTR, errno.ECHILD):
                    raise
            except KeyboardInterrupt:
                LOG.info(_LI('Caught keyboard interrupt. Exiting.'))
                os.killpg(0, signal.SIGTERM)
                break
        eventlet.greenio.shutdown_safe(self.sock)
        self.sock.close()
        LOG.debug('Server exited')

    def wait(self):
        """Wait until all servers have completed running."""
        try:
            if self.children:
                self.wait_on_children()
            else:
                self.pool.waitall()
        except KeyboardInterrupt:
            pass

    def run_child(self):
        pid = os.fork()
        if pid == 0:
            signal.signal(signal.SIGHUP, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            self.run_server()
            LOG.debug('Child %d exiting normally', os.getpid())
            return
        else:
            LOG.info(_LI('Started child %s'), pid)
            self.children.append(pid)

    def run_server(self):
        """Run a WSGI server."""
        self.pool = eventlet.GreenPool(size=self.threads)
        wsgi.server(self.sock,
                    self.application,
                    custom_pool=self.pool,
                    log=loggers.WritableLogger(LOG),
                    debug=False)
        self.pool.waitall()

    def _single_run(self, application, sock):
        """Start a WSGI server in a new green thread."""
        LOG.info(_LI("Starting single process server"))
        eventlet.wsgi.server(sock, application,
                             custom_pool=self.pool,
                             log=loggers.WritableLogger(LOG),
                             debug=False)
