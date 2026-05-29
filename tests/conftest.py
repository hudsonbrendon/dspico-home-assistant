"""Fixtures for DSpico tests."""
import pytest


@pytest.fixture()
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in tests that use hass."""
    yield
