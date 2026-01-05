"""
Tests for the --docker-compose-wait feature.

These tests verify that when --docker-compose-wait is used, containers
are healthy (based on their healthcheck definitions) before tests run.
"""

import pytest
import requests

pytestmark = pytest.mark.wait_for_healthcheck


@pytest.fixture(scope="function")
def api_service(function_scoped_container_getter):
    """Get the API service container."""
    container = function_scoped_container_getter.get("my_api_service")
    assert hasattr(container, "network_info")
    assert container.network_info
    return container


def test_container_is_healthy_when_wait_flag_used(api_service):
    """
    When --docker-compose-wait is used, the container should already be healthy
    by the time the test runs, meaning we can immediately make requests without
    any retry logic.
    """
    network_info = api_service.network_info[0]
    api_url = f"http://{network_info.hostname}:{network_info.host_port}/"

    # With --docker-compose-wait, the service should be immediately available
    # without needing retry logic
    response = requests.get(api_url, timeout=5)
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_db_container_is_healthy(function_scoped_container_getter):
    """
    Verify the database container is also healthy when --docker-compose-wait is used.
    """
    container = function_scoped_container_getter.get("my_db")
    # Container should be running and healthy
    assert container.state.running
    # When using --docker-compose-wait, the health status should be "healthy"
    assert container.state.health is not None
    assert container.state.health.status == "healthy"