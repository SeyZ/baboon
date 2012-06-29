from threading import Thread

from bottle import get, post, delete, request, response
from bottle import run as listen
from sleekxmpp.exceptions import IqError
from baboond.transport import transport


class Http(Thread):

    def __init__(self):
        Thread.__init__(self)

    def run(self):
        listen(host='0.0.0.0', port=8080)

    @staticmethod
    def xmpp_request(method_name, *args, **kwargs):
        """ Calls the method_name from the transport by passing args and
        kwargs.

        Handles possible XMPP errors and map them into HTTP errors.
        """

        try:
            return getattr(transport, method_name)(*args, **kwargs)
        except IqError as e:
            response.status = int(e.iq['error']['code'])
            return e.iq['error']['condition']

    @staticmethod
    @get('/projects')
    def get_projects():
        res = Http.xmpp_request('get_nodes')
        return '\n'.join([x[1] for x in res['disco_items']['items']])

    @staticmethod
    @post('/projects')
    def create_project():
        data = request.body.readline()
        Http.xmpp_request('create_node', data)

    @staticmethod
    @delete('/projects/:name')
    def delete_project(name):
        return Http.xmpp_request('delete_node', name)

http = Http().start()
