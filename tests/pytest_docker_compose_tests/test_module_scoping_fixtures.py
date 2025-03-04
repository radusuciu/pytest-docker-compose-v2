import time
import requests
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import pytest

pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="module")
def wait_for_api(module_scoped_container_getter):
    """Wait for the api from my_api_service to become responsive"""
    request_session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    request_session.mount("http://", HTTPAdapter(max_retries=retries))

    container = module_scoped_container_getter.get("my_api_service")
    assert hasattr(container, "network_info")
    assert container.network_info

    network_info = container.network_info[0]
    api_url = "http://%s:%s/" % (network_info.hostname, network_info.host_port)
    assert request_session.get(api_url)

    start = time.time()
    while (
        "exited"
        not in module_scoped_container_getter.get("my_short_lived_service").state.status
    ):
        if time.time() - start >= 5:
            raise RuntimeError(
                'my_short_lived_service should spin up, echo "Echoing" and '
                "then shut down, since it still running something went wrong"
            )
        time.sleep(0.5)
    return request_session, api_url


@pytest.fixture
def do_an_insert(wait_for_api):
    """Insert data to the database in the container my_db"""
    request_session, api_url = wait_for_api
    item_url = "items/1"
    data_string = "some_data"
    request_session.put("%s%s?data_string=%s" % (api_url, item_url, data_string))
    yield item_url, data_string
    request_session.delete(urljoin(api_url, item_url)).json()


def test_read_an_item(wait_for_api, do_an_insert):
    request_session, api_url = wait_for_api
    item_url, data_string = do_an_insert
    item = request_session.get(api_url + item_url).json()
    assert item["data"] == data_string


def test_read_and_write(wait_for_api):
    request_session, api_url = wait_for_api
    data_string = "some_other_data"
    request_session.put("%sitems/2?data_string=%s" % (api_url, data_string))
    item = request_session.get(urljoin(api_url, "items/2")).json()
    assert item["data"] == data_string
    request_session.delete(urljoin(api_url, "items/2"))


def test_read_all(wait_for_api):
    request_session, api_url = wait_for_api
    assert len(request_session.get(urljoin(api_url, "items/all")).json()) == 0


if __name__ == "__main__":
    pytest.main(["--docker-compose", "./my_network", "--docker-compose-no-build"])
