import functools
import json
import os
import uuid

from tornado import ioloop, testing
import motor

from . import web
import dockertest


class Fixture(object):

    def __init__(self):
        self.db_name = 'db{0}'.format(uuid.uuid4().hex)
        collection_names = ['c{0}'.format(uuid.uuid4().hex)
                            for _ in range(0, 10)]
        self.collections = {}
        for _ in range(0, 10):
            name = 'c{0}'.format(uuid.uuid4().hex)
            self.collections[name] = [{'name': '{0}'.format(uuid.uuid4().hex)}
                                      for _ in range(0, 10)]
        self.installed = False
        self._mongo = {}

    @property
    def mongo_client(self):
        if not self._mongo:
            self._mongo['host'] = os.environ['MONGO_PORT_27017_TCP_ADDR']
            self._mongo['port'] = int(os.environ['MONGO_PORT_27017_TCP_PORT'])
        return motor.MotorClient(**self._mongo)

    def install(self, iol):
        if not self.installed:
            for name, documents in self.collections.items():
                collection = self.mongo_client[self.db_name][name]
                for doc in documents:
                    iol.run_sync(functools.partial(collection.insert, doc))
            self.installed = True

    def uninstall(self, iol):
        iol.run_sync(
            functools.partial(self.mongo_client.drop_database, self.db_name))
        self.installed = False


_fixture = Fixture()


def teardown_module():
    _fixture.uninstall(ioloop.IOLoop.instance())


class TestRootHandler(dockertest.TestCase, testing.AsyncHTTPTestCase):

    def get_app(self):
        return web.make_application(debug=True)

    def setUp(self):
        super(TestRootHandler, self).setUp()
        _fixture.install(self.io_loop)

    def test_that_root_handler_returns_json(self):
        response = self.fetch('/')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-Type'],
                         'application/json; charset=utf8')

    def test_that_root_handler_returns_database(self):
        response = self.fetch('/')
        self.assertEqual(response.code, 200)
        body = json.loads(response.body.decode('utf-8'))
        self.assertIn(_fixture.db_name,
                      [info['name'] for info in body])
