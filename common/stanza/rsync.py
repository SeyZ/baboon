from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase, ET
from sleekxmpp import Iq

from common.file import FileEvent


class Rsync(ElementBase):
    name = 'rsync'
    namespace = 'baboon'
    plugin_attrib = 'rsync'
    interfaces = set(('sid', 'rid', 'node', 'files', 'create_files',
        'move_files', 'delete_files', 'first_rsync'))
    sub_interfaces = set(('files', 'create_files', 'move_files',
        'delete_files', 'first_rsync'))

    def get_files(self):

        files = []

        for element in self.xml.getchildren():
            tag_name = element.tag.split('}', 1)[-1]
            file_event_type = None

            if tag_name == 'file':
                file_event_type = FileEvent.MODIF
            elif tag_name == 'create_file':
                file_event_type = FileEvent.CREATE
            elif tag_name == 'move_file':
                file_event_type = FileEvent.MOVE
            elif tag_name == 'delete_file':
                file_event_type = FileEvent.DELETE
            elif tag_name == 'first_rsync':
                file_event_type = FileEvent.FIRST_RSYNC

            file_event = FileEvent(self['node'], file_event_type, element.text)
            files.append(file_event)

        return files

    def add_file(self, f):
        file_xml = ET.Element('{%s}file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_files(self, files):
        for f in files:
            self.add_file(f)

    def add_create_file(self, f):
        file_xml = ET.Element('{%s}create_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_create_files(self, files):
        for f in files:
            self.add_create_file(f)

    def add_delete_file(self, f):
        file_xml = ET.Element('{%s}delete_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_delete_files(self, files):
        for f in files:
            self.add_delete_file(f)

    def add_move_file(self, f):
        file_xml = ET.Element('{%s}move_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_move_files(self, files):
        for f in files:
            self.add_move_file(f)

    def add_first_rsync(self, f):
        file_xml = ET.Element('{%s}first_rsync' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)


class RsyncFinished(ElementBase):
    name = 'rsyncfinished'
    namespace = 'baboon'
    interfaces = set(tuple())
    plugin_attrib = 'rsyncfinished'


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
register_stanza_plugin(Iq, RsyncFinished)
register_stanza_plugin(Iq, MergeVerification)
register_stanza_plugin(Iq, MergeStatus)
