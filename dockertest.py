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


class DockerDiscoveryMixin(EnvironmentMixin):
    """
    Mix-in that discovers services exposed by a docker host.

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
        super(DockerDiscoveryMixin, cls).setUpClass()

        curdir = os.path.abspath(os.path.curdir)
        dirname = os.path.basename(curdir)
        cls.docker_compose_project = re.sub('[^A-Za-z0-9]', '', dirname)
        cls.docker_services = {}

        cls._connect_to_docker()
        for container_info in cls.docker_client.containers():
            try:
                details = cls._extract_container_details(container_info)
                if details:
                    cls.docker_services.update(details)

            except KeyError:
                _logger.debug('skipping container %s', container_info['Id'],
                              exc_info=True)

    @classmethod
    def tearDownClass(cls):
        if cls.docker_client:
            cls.docker_client.close()
            cls.docker_client = None
        super(DockerDiscoveryMixin, cls).tearDownClass()


    @classmethod
    def _connect_to_docker(cls):
        args = docker.utils.kwargs_from_env()
        try:
            args['tls'].assert_hostname = False
        except KeyError:
            pass

        cls.docker_client = docker.Client(**args)
        docker_url = parse.urlsplit(cls.docker_client.base_url)
        cls.docker_ip = docker_url.hostname

    @classmethod
    def _extract_container_details(cls, container_info):
        project = cls.docker_compose_project
        labels = container_info['Labels']
        if (labels['com.docker.compose.project'] !=
                cls.docker_compose_project):
            _logger.debug('skipping %s, wrong project %s',
                          container_info['id'],
                          labels['com.docker.compose.project'])
            return

        service_name = labels['com.docker.compose.service']
        service = cls._NAME_RE.sub('_', service_name).upper()
        details = {}
        for port_info in container_info['Ports']:
            key = '{0}:{1}'.format(service_name, port_info['PrivatePort'])
            details[key] = {'protocol': port_info['Type'],
                            'ip_address': cls.docker_ip,
                            'public_port': port_info['PublicPort'],
                            'private_port': port_info['PrivatePort']}
            _logger.debug('added %s => %r', key, details[key])

        return details


class TestCase(DockerDiscoveryMixin, EnvironmentMixin, unittest.TestCase):
    """
    Test case imbued with Docker super powers.

    When your tests run, they can make use of environment as if
    they were running in a docker container linked into the active
    docker compose environment.  The :meth:`install_docker_environment`
    method is called to install the docker environment variables in
    :meth:`setUp`, so they will be available to your test code.

    """

    def setUp(self):
        """Install the docker linking environment variables."""
        self.install_docker_environment()
        super(TestCase, self).setUp()

    def install_docker_environment(self):
        """
        Creates environment variables based on :attr:`docker_services`

        This method walks the :attr:`docker_services` attribute and exports
        a handful of environment variables for each service port.  For a
        service named ``$SERVICE`` that listens on a well-known ``$PROTOCOL``
        port ``$PORT`` the following environment variables will be exposed:

        - **${SERVICE}_PORT_${PORT}_${PROTOCOL}** the endpoint information
          as a URL using ``tcp`` or ``udp`` as the scheme.
        - **${SERVICE}_PORT_${PORT}_${PROTOCOL}_ADDR** the IP address that
          the service is available on.  This is the IP address of the
          docker host.
        - **${SERVICE}_PORT_${PORT}_${PROTOCOL}_PORT** the port number on
          the docker host that is routed to the service.
        - **${SERVICE}_PORT_${PORT}_${PROTOCOL}_PROTO** the protocol that
          owns the port number (e.g., UDP, TCP)

        For example, if a database instance is listening on port 5432 and
        the docker host, 192.168.99.100, exposes the service on port 32768,
        then the following environment variables are exported

        .. code-block:: bash

            POSTGRES_PORT_5432_TCP=tcp://192.168.99.100:32768
            POSTGRES_PORT_5432_TCP_ADDR=192.168.99.100
            POSTGRES_PORT_5432_TCP_PORT=32768
            POSTGRES_PORT_5432_TCP_PROTO=tcp

        """
        for service_key, service_info in self.docker_services.items():
            service_name, _ = service_key.split(':')
            self.process_docker_service(service_name, **service_info)

    def process_docker_service(self, name, protocol, ip_address,
            public_port, private_port):
        """
        Process a single docker service entry.

        :param str name: name of the service as docker-compose knows it
        :param str protocol: service protocol (usually ``tcp``)
        :param str ip_address: IP address that the service is available on
        :param int public_port: port that the service is available on.  This
            port is bound on the docker host (e.g., ``ip_address``).
        :param int private_port: internal port that the service is listening
            on.  This is the port that the application is listening on
            inside of the container.

        You can override or extend this method to set any application
        specific environment variables.

        """
        _logger.debug('setting environment for %s', name)
        base_key = '{0}_PORT_{1}_{2}'.format(name.upper(), private_port,
                                             protocol.upper())
        self.setenv(base_key, '{0}://{1}:{2}'.format(protocol, ip_address,
                                                     public_port))
        self.setenv(base_key + '_ADDR', ip_address)
        self.setenv(base_key + '_PORT', public_port)
        self.setenv(base_key + '_PROTO', protocol)

