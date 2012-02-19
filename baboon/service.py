

class Service(object):
    def __init__(self):
        print "Service builder !"

    def send(self, patch):
        print "Sending the patch %s" % patch


service = Service()
