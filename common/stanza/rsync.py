from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase
from sleekxmpp import Iq


class RsyncStart(ElementBase):
    name = 'rsync_start'
    namespace = 'baboon'
    interfaces = set(('node',))
    plugin_attrib = 'rsync_start'


class RsyncOk(ElementBase):
    name = 'rsync_ok'
    namespace = 'baboon'
    interfaces = set(('req_id', 'remote_dir'))
    plugin_attrib = 'rsync_ok'


class RsyncStop(ElementBase):
    name = 'rsync_stop'
    namespace = 'baboon'
    interfaces = set(('node', 'req_id'))
    plugin_attrib = 'rsync_stop'


class RsyncFinished(ElementBase):
    name = 'rsync_finished'
    namespace = 'baboon'


class MergeStatus(ElementBase):
    name = 'merge_status'
    namespace = 'baboon'
    interfaces = set(('node', 'status'))
    plugin_attrib = 'status'

register_stanza_plugin(Iq, RsyncStart)
register_stanza_plugin(Iq, RsyncOk)
register_stanza_plugin(Iq, RsyncStop)
register_stanza_plugin(Iq, MergeStatus)
