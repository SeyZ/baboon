from bottle import get, post, delete, run, request, response
from sleekxmpp.exceptions import IqError
from transport import transport


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


@get('/projects')
def get_projects():
    res = xmpp_request('get_nodes')
    return '\n'.join([x[1] for x in res['disco_items']['items']])


@post('/projects')
def create_project():
    data = request.body.readline()
    xmpp_request('create_node', data)


@delete('/projects/:name')
def delete_project(name):
    return xmpp_request('delete_node', name)


def listen(**kwargs):
    run(**kwargs)
