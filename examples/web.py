#!/usr/bin/env python

import logging
import signal

from tornado import ioloop, web


_logger = logging.getLogger(__name__)


class MongoCollectionHandler(web.RequestHandler):
    pass


class MongoDocumentHandler(web.RequestHandler):
    pass


def make_application(**settings):
    return web.Application([
        web.url(r'/collections', MongoCollectionHandler),
        web.url(r'/collection/(?P<name>\w+)', MongoCollectionHandler),
        web.url(r'/document/(?P<doc_id>\w+)', MongoDocumentHandler),
    ], **settings)


def _signal_handler(signo, frame):
    _logger.info('caught signal #%d, stopping IOLoop', signo)
    iol = ioloop.IOLoop.instance()
    iol.add_callback_from_signal(iol.stop)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    app = make_application(debug=True)
    app.listen(8000)
    ioloop.IOLoop.instance().start()
