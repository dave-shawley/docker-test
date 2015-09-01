Docker Testing Utilities
========================
This module injects environment variables into your tests to match the
currently running docker environment.  The goal is to make testing with
servers from a local docker compose enviroment available to your tests
without having to manage the ephemeral ports of the services yourself.

`Docker linking`_ makes the exposed ports of docker containers available
as environment variables with formulated names.  Docker-compose goes
a step further and encodes the project (e.g., directory) name, the
service name, and each exposed port into separate sets of environment
variables.  The ``dockertest.DockerEnvironmentMixin`` queries the local
docker host and configures environment variables to mimic what docker
compose would have done.  This makes it simple to write tests that use
services in a docker-compose environment.

.. _Docker linking: https://docs.docker.com/userguide/dockerlinks/#communication-across-links
