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


def patch_minidom_writexml():
    """Patch for xml.dom.minidom toprettyxml bug with whitespaces around text

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

    def writexml(self, writer, indent="", addindent="", newl=""):
        # indent = current indentation
        # addindent = indentation to add to higher levels
        # newl = newline string
        writer.write(indent + "<" + self.tagName)

        attrs = self._get_attributes()
        a_names = attrs.keys()
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

    md.Element.writexml = writexml

    def writexml(self, writer, indent="", addindent="", newl=""):
        md._write_data(writer, "%s%s%s" % (indent, self.data, newl))

    md.Text.writexml = writexml
