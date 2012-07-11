from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase, ET
from sleekxmpp import Iq


class Rsync(ElementBase):
    name = 'rsync'
    namespace = 'baboon'
    plugin_attrib = 'rsync'
    interfaces = set(('sid', 'node', 'files', 'move_files', 'delete_files'))
    sub_interfaces = set(('files', 'move_files', 'delete_files'))

    def get_files(self):
        results = []
        files = self.xml.findall('{%s}file' % self.namespace)

        if files is not None:
            for f in files:
                results.append(f.text)

        return results

    def add_file(self, f):
        file_xml = ET.Element('{%s}file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_files(self, files):
        for f in files:
            self.add_file(f)

    def get_delete_files(self):
        results = []
        del_files = self.xml.findall('{%s}delete_file' % self.namespace)

        if del_files is not None:
            for f in del_files:
                results.append(f.text)

        return results

    def add_delete_file(self, f):
        file_xml = ET.Element('{%s}delete_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_delete_files(self, files):
        for f in files:
            self.add_delete_file(f)

    def get_move_files(self):
        results = []
        mov_files = self.xml.findall('{%s}move_file' % self.namespace)

        if mov_files is not None:
            for f in mov_files:
                results.append(f.text)

        return results

    def add_move_file(self, f):
        file_xml = ET.Element('{%s}move_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_move_files(self, files):
        for f in files:
            self.add_move_file(f)


class MergeVerification(ElementBase):
    name = 'merge_verification'
    namespace = 'baboon'
    interfaces = set(('node', ))
    plugin_attrib = 'merge'


class MergeStatus(ElementBase):
    name = 'merge_status'
    namespace = 'baboon'
    interfaces = set(('node', 'status'))
    plugin_attrib = 'status'

register_stanza_plugin(Iq, Rsync)
register_stanza_plugin(Iq, MergeVerification)
register_stanza_plugin(Iq, MergeStatus)
