#!/usr/bin/env python

import json
import logging
import os
import signal

from tornado import gen, ioloop, web
import motor
import pymongo.errors


_logger = logging.getLogger(__name__)


class MongoHandler(web.RequestHandler):

    def initialize(self):
        super(MongoHandler, self).initialize()
        self.logger = _logger.getChild(self.__class__.__name__)

    def reverse_url(self, name, *args, **kwargs):
        absolute = kwargs.pop('absolute', False)
        result = super(MongoHandler, self).reverse_url(name, *args, **kwargs)
        if not absolute:
            return result

        return '{0}://{1}{2}'.format(self.request.protocol,
                                     self.request.host, result)

    @gen.coroutine
    def prepare(self):
        maybe_future = super(MongoHandler, self).prepare()
        if maybe_future:
            yield maybe_future
        if not self._finished:
            try:
                self.mongo = yield self.application.mongo.open()
            except pymongo.errors.ConnectionFailure:
                self.logger.exception('failed to connect to mongo')
                raise web.HTTPError(500)


class MongoRootHandler(MongoHandler):

    @gen.coroutine
    def get(self):
        dbs = []
        for db_name in (yield self.mongo.database_names()):
            dbs.append({
                'name': db_name,
                'link': self.reverse_url('db-handler', db_name, absolute=True),
            })
        self.set_header('Content-Type', 'application/json; charset=utf8')
        self.write(json.dumps(dbs).encode('utf-8'))


class MongoDatabaseHandler(MongoHandler):
    pass


class MongoCollectionHandler(MongoHandler):
    pass


class MongoDocumentHandler(MongoHandler):
    pass


def make_application(**settings):
    app = web.Application([
        web.url(r'/', MongoRootHandler),
        web.url(r'/database/(?P<name>\w+)', MongoDatabaseHandler,
                name='db-handler'),
        web.url(r'/collection/(?P<name>\w+)', MongoCollectionHandler,
                name='collection-handler'),
        web.url(r'/document/(?P<doc_id>\w+)', MongoDocumentHandler,
                name='document-handler'),
    ], **settings)
    setattr(app, 'mongo', motor.MotorClient(
        host=os.environ['MONGO_PORT_27017_TCP_ADDR'],
        port=int(os.environ['MONGO_PORT_27017_TCP_PORT']),
    ))
    return app


def _signal_handler(signo, frame):
    _logger.info('caught signal #%d, stopping IOLoop', signo)
    iol = ioloop.IOLoop.instance()
    iol.add_callback_from_signal(iol.stop)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)1.1s %(name)s: %(message)s')
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    app = make_application(debug=True)
    app.listen(8000)
    ioloop.IOLoop.instance().start()
