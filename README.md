[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pytest-docker-compose-v2.svg)](https://pypi.python.org/pypi/pytest-docker-compose-v2/)
[![PyPI version](https://img.shields.io/pypi/v/pytest-docker-compose-v2.svg)](https://pypi.python.org/pypi/pytest-docker-compose-v2/)
[![GitHub release](https://img.shields.io/github/release/radusuciu/pytest-docker-compose-v2.svg)](https://github.com/radusuciu/pytest-docker-compose-v2/releases/)

# pytest-docker-compose-v2

**NOTE**: This is a fork from the [`pytest-docker-compose`](https://github.com/pytest-docker-compose/pytest-docker-compose) project which at the time of writing hasn't been updated in 2 years -- I depend on this so I'm taking a crack at running a -v2 fork, but I'm definitely willing to re-integrate any changes back to the original project. Currently the changes are pretty basic and include [a PR that introduces support for docker compose v2](https://github.com/pytest-docker-compose/pytest-docker-compose/pull/98/), some package updates, and more superficial updates to align with personal preferences. Though I am making an effort to run the existing test suite, I have not tested this extensively.

This package contains a `pytest` plugin for integrating Docker Compose into your automated integration tests.

Given a path to a `docker-compose.yml` file, it will automatically build the project at the start of the test run, bring the containers up before each test starts, and tear them down after each test ends.


## Dependencies

Make sure you have [Docker](https://docs.docker.com/get-docker/) installed.

This plugin is automatically tested against the following software:

- Python 3.10, 3.11, 3.12, 3.13 and 3.14
- pytest 7, 8 and 9

**NOTE**: This plugin is **not** compatible with Python 2.


## Installation

Install the plugin using pip:

```shell
pip install pytest-docker-compose-v2
```

## Usage

The plugin is automatically enabled when installed. To disable it for specific test runs, use:

```shell
pytest -p no:docker_compose
```

To interact with Docker containers in your tests, use the following fixtures. These fixtures tell docker-compose to start all the services and then fetch the associated containers for use in a test:

### `function_scoped_container_getter`

An object that fetches containers of the Docker `python_on_whales.Container` objects running during the test. The containers are fetched using `function_scoped_container_getter.get('service_name')` These containers each have an extra attribute called `network_info` added to them. This attribute has a list of `pytest_docker_compose.NetworkInfo` objects.

This information can be used to configure API clients and other objects that will connect to services exposed by the Docker containers in your tests.

`NetworkInfo` is a container with the following fields:

- `container_port`: The port (and usually also protocol name) exposed
    internally to the container.  You can use this value to find the correct
    port for your test, when the container exposes multiple ports.
- `hostname`: The hostname (usually "localhost") to use when connecting to
    the service from the host.
- `host_port`: The port number to use when connecting to the service from
    the host.

### `docker_project`

The `python_on_whales.DockerClient` object that the containers are built from.
This fixture is generally only used internally by the plugin.

### Wider scoped fixtures

To use the following fixtures please read [Use wider scoped fixtures](#use-wider-scoped-fixtures)

- `class_scoped_container_getter`: Similar to `function_scoped_container_getter` just with a wider scope.
- `module_scoped_container_getter`: Similar to `function_scoped_container_getter` just with a wider scope.
- `session_scoped_container_getter`: Similar to `function_scoped_container_getter` just with a wider scope.

### Waiting for Services to Come Online

The fixtures called `[scope]_scoped_container_getter` will wait until every container is up before handing control over to the test.

However, just because a container is up does not mean that the services running on it are ready to accept incoming requests yet!

If your tests need to wait for a particular condition (for example, to wait for an HTTP health check endpoint to send back a 200 response), make sure that your fixtures account for this.

Here's an example of a fixture called `wait_for_api` that waits for an HTTP service to come online before a test called `test_read_and_write` can run.

```python
import pytest
import requests
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Invoking this fixture: 'function_scoped_container_getter' starts all services
@pytest.fixture(scope="function")
def wait_for_api(function_scoped_container_getter):
    """Wait for the api from my_api_service to become responsive"""
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    service = function_scoped_container_getter.get("my_api_service").network_info[0]
    api_url = "http://%s:%s/" % (service.hostname, service.host_port)
    assert request_session.get(api_url)
    return request_session, api_url


def test_read_and_write(wait_for_api):
    """The Api is now verified good to go and tests can interact with it"""
    request_session, api_url = wait_for_api
    data_string = 'some_data'
    request_session.put('%sitems/2?data_string=%s' % (api_url, data_string))
    item = request_session.get(urljoin(api_url, 'items/2')).json()
    assert item['data'] == data_string
    request_session.delete(urljoin(api_url, 'items/2'))
```

## Use wider scoped fixtures

The `function_scoped_container_getter` fixture uses "function" scope, meaning that all of the containers are torn down after each individual test.

This is done so that every test gets to run in a "clean" environment. However, this can potentially make a test suite take a very long time to complete.

There are two options to make containers persist beyond a single test. The best way is to use the fixtures that are explicitly scoped to different scopes. There are three additional fixtures for this purpose: `class_scoped_container_getter`, `module_scoped_container_getter` and `session_scoped_container_getter`. Notice that you need to be careful when using these! There are two main caveats to keep in mind:

1. Manage your scope correctly, using 'module' scope and 'function' scope in one single file will throw an error! This is because the module scoped fixture will spin up the containers and then the function scoped fixture will try to spin up the containers again. Docker compose does not allow you to spin up containers twice.
2. Clean up your environment after each test. Because the containers are not restarted their environments can carry the information from previous tests. Therefore you need to be very careful when designing your tests such that they leave the containers in the same state that it started in or you might run into difficult to understand behaviour.

A second method to make containers persist beyond a single test is to supply the `--use-running-containers` flag to pytest like so:

```shell
pytest --use-running-containers
```

With this flag, `pytest-docker-compose` checks that all containers are running
during the project creation. If they are not running a warning is given and
they are spun up anyways. They are then used for all the tests and NOT TORN
DOWN afterwards.

This mode is best used in combination with the `--docker-compose-no-build` flag since the newly build containers won't be used anyways. like so:

```shell
pytest --docker-compose-no-build --use-running-containers
```

It is of course possible to add these options to `pytest.ini` or `pyproject.toml`.

Notice that for this mode the scoping of the fixtures becomes less important since the containers are fully persistent throughout all tests. I only recommend using this if your network takes excessively long to spin up/tear down. It should really be a last resort and you should probably look into speeding up your network instead of using this.


## Running Integration Tests

Use `pytest` to run your tests as normal:

```shell
pytest
```

By default, this will look for a `docker-compose.yml` file in the current
working directory.  You can specify a different file via the
`--docker-compose` option:

```shell
pytest --docker-compose=/path/to/docker-compose.yml
```

Docker compose allows for specifying multiple compose files as described [in the docs](https://docs.docker.com/compose/extends). To specify more than one compose file, separate them with a `,`:

```shell
pytest --docker-compose=/path/to/docker-compose.yml,/another/docker-compose.yml,/third/docker-compose.yml
```


### Tip

Alternatively, you can specify this option in your `pytest.ini` file:

```ini
[pytest]
addopts = --docker-compose=/path/to/docker-compose.yml
```


The option will be ignored for tests that do not use this plugin.

See [Configuration Options](https://docs.pytest.org/en/stable/reference/customize.html#adding-default-options) for more information on using configuration
files to modify pytest behavior.

### Remove volumes after tests

There is another configuration option that will delete the volumes of containers after running.

```shell
pytest --docker-compose-remove-volumes
```

This option will be ignored if the plugin is not used. Again, this option can also be added to the `pytest.ini` file.

For more examples on how to use this plugin look at the testing suite of this plugin itself! It will give you some examples for configuring `pyproject.toml` and how to use the different fixtures to run docker containers.

