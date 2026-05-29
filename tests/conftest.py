"""Fixtures for DSpico tests."""
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    """Enable custom integrations only for tests that use Home Assistant.

    The plugin's ``enable_custom_integrations`` fixture depends on the async
    ``hass`` fixture, so forcing it onto pure-sync tests fails. Pulling it in
    conditionally keeps it effectively autouse for HA tests while leaving sync
    tests (e.g. the manifest smoke test) untouched.
    """
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")
    yield
