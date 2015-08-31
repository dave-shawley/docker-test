import logging
import os.path
import re
import unittest
try:
    from urllib import parse
except ImportError:  # pragma: no cover
    import urllib as parse

# Import hackery to make import the module from setup.py work
# without having py-docker installed.  This will also fail
# gracefully at runtime if you try to use it without having
# py-docker installed.
try:
    import docker.utils
except ImportError:  # pragma: no cover
    class docker(object):
        class Client(object):
            def __init__(self, *args, **kwargs):
                raise RuntimeError('failed to import docker')

        class utils(object):
            @staticmethod
            def kwargs_from_env():
                raise RuntimeError('failed to import docker')


version_info = (0, 0, 0)
__version__ = '.'.join(str(v) for v in version_info)

_logger = logging.getLogger(__name__)


class EnvironmentMixin(object):
    """
    Safely manages environment variables.

    This mix-in adds methods that get, set, and unset environment
    variables from within a test that guarantee that the starting
    environment is restored when the test completes.  Simple setting
    and clearing :data:`os.environ` seems like the thing to do while
    you are testing, but it increases test fragility due to environment
    variable leakage.  This class remoes that possibility while not
    inserting too much complexity.

    """

    _env_cache = {}

    def tearDown(self):
        super(EnvironmentMixin, self).tearDown()
        for name, value in self._env_cache.items():
            os.environ.pop(name, None)
            if value is not None:
                os.environ[name] = value
        self._env_cache.clear()

    @staticmethod
    def getenv(name, default=None):
        """Fetch the current value of the environment variable ``name``."""
        return os.environ.get(name, default)

    @classmethod
    def setenv(cls, name, value):
        """
        Set the environment variable ``name`` to ``value``.

        :param str name: name of the environment variable to set
        :param value: value for the variable.  This will be converted
            to a :class:`str` before it is stored in the environment.

        This method ensures that the starting environment variable value
        is cached and restored when :meth:`tearDown` is invoked.

        """
        cls._env_cache.setdefault(name, os.environ.get(name))
        _logger.debug('setting environment variable %s=%s', name, value)
        os.environ[name] = str(value)

    @classmethod
    def unsetenv(cls, name):
        """
        Clear the environment variable named ``name``.

        :param str name: name of the environment variable to clear

        This method ensures that the starting environment variable value
        is cached and restored when :meth:`tearDown` is invoked.

        """
        cls._env_cache.setdefault(name, os.environ.get(name))
        os.environ.pop(name, None)


class DockerEnvironmentMixin(object):
    """
    Mix-in that mimics the environment variables set by docker linking.

    .. attribute:: docker_services

       A :class:`dict` that maps each available docker service to a
       :class:`dict` of information about the service.  The following
       keys are present in the service information:

       - *protocol* the Internet protocol that the service is exposed
         over.  This is either ``tcp`` or ``udp``.
       - *ip_address* the IP address that the service is available on.
         This is usually the Docker host IP address.
       - *public_port* the TCP/UDP port that the service is available
         on via the *ip_address*.
       - *private_port* the TCP/UDP port that the service is actually
         listening on within the Docker container.

       The key for the ``docker_services`` dictionary is the name of
       the docker service and its port separated by a colon.

    """

    _NAME_RE = re.compile('[^A-Za-z0-9_]')

    @classmethod
    def setUpClass(cls):
        """Query docker host and build :attr:`docker_services`"""
        super(DockerEnvironmentMixin, cls).setUpClass()
        args = docker.utils.kwargs_from_env()
        try:
            args['tls'].assert_hostname = False
        except KeyError:
            pass

        cls.docker_client = docker.Client(**args)
        docker_url = parse.urlsplit(cls.docker_client.base_url)
        cls.docker_ip = docker_url.hostname

        curdir = os.path.abspath(os.path.curdir)
        dirname = os.path.basename(curdir)
        cls.docker_compose_project = re.sub('[^A-Za-z0-9]', '', dirname)
        cls.docker_services = {}

        for container_info in cls.docker_client.containers():
            try:
                labels = container_info['Labels']
                if (labels['com.docker.compose.project'] !=
                        cls.docker_compose_project):
                    _logger.debug('skipping %s, project is %s',
                                  container_info['Id'],
                                  labels['com.docker.compose.project'])
                    continue

                service_name = labels['com.docker.compose.service']
                service = cls._NAME_RE.sub('_', service_name).upper()
                for port_info in container_info['Ports']:
                    key = '{0}:{1}'.format(service_name,
                                           port_info['PrivatePort'])
                    cls.docker_services[key] = {
                        'protocol': port_info['Type'],
                        'ip_address': cls.docker_ip,
                        'port': port_info['PublicPort'],
                        'internal-port': port_info['PrivatePort'],
                    }
                    _logger.debug('added %s => %r', key,
                                  cls.docker_services[key])

            except KeyError:
                _logger.debug('skipping container %s', container_info['Id'],
                              exc_info=True)

    @classmethod
    def tearDownClass(cls):
        if cls.docker_client:
            cls.docker_client.close()
            cls.docker_client = None
        super(DockerEnvironmentMixin, cls).tearDownClass()

    def install_docker_environment(self):
        """
        Creates environment variables based on :attr:`docker_services`
        """
        for service_key, service_info in self.docker_services.items():
            service_name, _ = service_key.split(':')
            self.process_docker_service(service_name.upper(),
                                        service_info['protocol'],
                                        service_info['ip_address'],
                                        service_info['internal-port'],
                                        service_info['port'])

    def process_docker_service(self, name, proto, ip, priv_port, pub_port):
        _logger.debug('setting environment for %s', name)
        base_key = '{0}_PORT_{1}_{2}'.format(name, priv_port, proto.upper())
        self.setenv(base_key, '{0}://{1}:{2}'.format(proto, ip, pub_port))
        self.setenv(base_key + '_ADDR', ip)
        self.setenv(base_key + '_PORT', pub_port)
        self.setenv(base_key + '_PROTO', proto)


class TestCase(EnvironmentMixin, DockerEnvironmentMixin, unittest.TestCase):

    def setUp(self):
        self.install_docker_environment()
        super(TestCase, self).setUp()
