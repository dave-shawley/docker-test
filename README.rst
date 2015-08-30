Docker Testing Utilities
========================
This module injects environment variables into your tests to match the
currently running docker environment.  The goal is to make testing with
servers from a local docker compose enviroment available to your tests
without having to manage the ephemeral ports of the services yourself.
