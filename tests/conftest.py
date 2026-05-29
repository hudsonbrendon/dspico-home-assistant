"""Fixtures for DSpico tests."""
import pytest


@pytest.fixture(scope="session", autouse=True)
def _prewarm_pycares_shutdown_thread():
    """Pre-start the pycares channel-shutdown daemon thread.

    pycares._shutdown_manager lazily starts a daemon thread the first time a
    DNS channel is destroyed. If that happens inside a test's teardown phase,
    verify_cleanup sees it as a new thread and fails. Starting it here, once at
    session scope, puts it in every test's ``threads_before`` baseline.
    """
    try:
        import pycares  # noqa: PLC0415

        pycares._shutdown_manager.start()  # noqa: SLF001
    except AttributeError:
        import warnings

        warnings.warn(
            "pycares._shutdown_manager not found; the verify_cleanup workaround "
            "in conftest.py may be obsolete. Check for spurious thread failures.",
            stacklevel=1,
        )
    except Exception:  # noqa: BLE001
        pass


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
