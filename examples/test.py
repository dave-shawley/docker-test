from tornado import testing

from . import web
import dockertest


class TestRootHandler(dockertest.TestCase, testing.AsyncHTTPTestCase):

    def get_app(self):
        return web.make_application(debug=True)
