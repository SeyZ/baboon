from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase
from sleekxmpp import Iq


class Rsync(ElementBase):
    name = 'rsync'
    namespace = 'baboon'
    interfaces = set(('sid', 'node'))
    plugin_attrib = 'rsync'


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
