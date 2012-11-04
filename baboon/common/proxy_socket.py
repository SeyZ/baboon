import sys
import logging
import pickle
import struct
import socket
import threading
import select


from baboon.common.logger import logger

logger = logging.getLogger(__name__)


def listen(sid, sock, callback):
    """ Starts listening on the socket associated to the SID for data. When
    data is receveid, call the callback.
    """

    thread = threading.Thread(target=_run, args=(sid, sock, callback))
    thread.start()


def _run(sid, sock, callback):
    """ A thread to listen data on the sock. This thread calls the callback
    when data is received.
    """

    socket_open = True
    while socket_open:
        ins = []
        try:
            # Wait any read available data on socket. Timeout
            # after 5 secs.
            ins, out, err = select.select([sock, ], [], [], 5)
        except socket.error as (errno, err):
            # 9 means the socket is closed. It can be normal. Otherwise,
            # log the error.
            if errno != 9:
                logger.debug('Socket is closed: %s' % err)
            break
        except Exception as e:
            logger.debug(e)
            break

        for s in ins:
            data = _recv_size(sock)
            if not data:
                socket_open = False
            else:
                unpacked_data = unpack(data)
                if unpacked_data:
                    callback(sid, unpacked_data)


def _recv_size(sock):
    """ Read data on the socket and return it.
    """

    total_len = 0
    total_data = []
    size = sys.maxint
    size_data = sock_data = ''
    recv_size = 8192

    while total_len < size:
        sock_data = sock.recv(recv_size)
        if not sock_data:
            return ''.join(total_data)

        if not total_data:
            if len(sock_data) > 4:
                size_data += sock_data
                size = struct.unpack('>i', size_data[:4])[0]
                recv_size = size
                if recv_size > 524288:
                    recv_size = 524288
                total_data.append(size_data[4:])
            else:
                size_data += sock_data
        else:
            total_data.append(sock_data)
        total_len = sum([len(i) for i in total_data])
    return ''.join(total_data)


def pack(data):
    """ Packs the data.
    """

    # The data format is: `len_data`+`data`. Useful to receive all the data
    # at once (avoid splitted data) thanks to the recv_size method.
    data = pickle.dumps(data)
    return struct.pack('>i', len(data)) + data


def unpack(data):
    """ Unpacks the data. On error, log an error message and returns None.
    """

    try:
        return pickle.loads(data)
    except Exception as err:
        logger.error(err)
