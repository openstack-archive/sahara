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

import eventlet


EVENTLET_MONKEY_PATCH_MODULES = dict(os=True,
                                     select=True,
                                     socket=True,
                                     thread=True,
                                     time=True)


def patch_all():
    """Apply all patches.

    List of patches:

    * eventlet's monkey patch for all cases;
    * minidom's writexml patch for py < 2.7.3 only.
    """
    eventlet_monkey_patch()
    patch_minidom_writexml()


def eventlet_monkey_patch():
    """Apply eventlet's monkey patch.

    This call should be the first call in application. It's safe to call
    monkey_patch multiple times.
    """
    eventlet.monkey_patch(**EVENTLET_MONKEY_PATCH_MODULES)


def eventlet_import_monkey_patched(module):
    """Returns module monkey patched by eventlet.

    It's needed for some tests, for example, context test.
    """
    return eventlet.import_patched(module, **EVENTLET_MONKEY_PATCH_MODULES)


def patch_minidom_writexml():
    """Patch for xml.dom.minidom toprettyxml bug with whitespaces around text

    We apply the patch to avoid excess whitespaces in generated xml
    configuration files that brakes Hadoop.

    (This patch will be applied for all Python versions < 2.7.3)

    Issue: http://bugs.python.org/issue4147
    Patch: http://hg.python.org/cpython/rev/cb6614e3438b/
    Description: http://ronrothman.com/public/leftbraned/xml-dom-minidom-\
                        toprettyxml-and-silly-whitespace/#best-solution
    """

    import sys
    if sys.version_info >= (2, 7, 3):
        return

    import xml.dom.minidom as md

    def element_writexml(self, writer, indent="", addindent="", newl=""):
        # indent = current indentation
        # addindent = indentation to add to higher levels
        # newl = newline string
        writer.write(indent + "<" + self.tagName)

        attrs = self._get_attributes()
        a_names = list(attrs.keys())
        a_names.sort()

        for a_name in a_names:
            writer.write(" %s=\"" % a_name)
            md._write_data(writer, attrs[a_name].value)
            writer.write("\"")
        if self.childNodes:
            writer.write(">")
            if (len(self.childNodes) == 1
                    and self.childNodes[0].nodeType == md.Node.TEXT_NODE):
                self.childNodes[0].writexml(writer, '', '', '')
            else:
                writer.write(newl)
                for node in self.childNodes:
                    node.writexml(writer, indent + addindent, addindent, newl)
                writer.write(indent)
            writer.write("</%s>%s" % (self.tagName, newl))
        else:
            writer.write("/>%s" % (newl))

    md.Element.writexml = element_writexml

    def text_writexml(self, writer, indent="", addindent="", newl=""):
        md._write_data(writer, "%s%s%s" % (indent, self.data, newl))

    md.Text.writexml = text_writexml
