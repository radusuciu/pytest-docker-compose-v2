"""
Tests for the docker compose --wait behavior.

These tests verify that containers are healthy (based on their healthcheck
definitions) before tests run. This is the default behavior of the plugin.
"""

import pytest
import requests


@pytest.fixture(scope="function")
def api_service(function_scoped_container_getter):
    """Get the API service container."""
    container = function_scoped_container_getter.get("my_api_service")
    assert hasattr(container, "network_info")
    assert container.network_info
    return container


def test_container_is_healthy_by_default(api_service):
    """
    With the default wait behavior, the container should already be healthy
    by the time the test runs, meaning we can immediately make requests without
    any retry logic.
    """
    network_info = api_service.network_info[0]
    api_url = f"http://{network_info.hostname}:{network_info.host_port}/"

    # With the default wait behavior, the service should be immediately available
    # without needing retry logic
    response = requests.get(api_url, timeout=5)
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_db_container_is_healthy(function_scoped_container_getter):
    """
    Verify the database container is also healthy with the default wait behavior.
    """
    container = function_scoped_container_getter.get("my_db")
    # Container should be running and healthy
    assert container.state.running
    # With the default wait behavior, the health status should be "healthy"
    assert container.state.health is not None
    assert container.state.health.status == "healthy"