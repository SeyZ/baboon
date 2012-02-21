from transport import Transport


class Service():
    def __init__(self):
        self.xmpp = Transport('seyz@localhost', 'secret')
        self.xmpp.register_plugin('xep_0030')  # Service Discovery
        self.xmpp.register_plugin('xep_0004')  # Data Forms
        self.xmpp.register_plugin('xep_0060')  # PubSub
        self.xmpp.register_plugin('xep_0199')  # XMPP Ping

    def start(self):
        if self.xmpp.connect():
            self.xmpp.process()
        else:
            print("Unable to connect.")

    def broadcast(self, patch):
        self.xmpp.broadcast(patch)


service = Service()
