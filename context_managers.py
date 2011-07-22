import os
from fabric.api import prefix
from contextlib import contextmanager

@contextmanager
def _DummyContext():
    """
    Dummy context object that can be returned in the event that no prefix()
    context object is required.
    """

    yield

def proxy(http_proxy=None, https_proxy=None):
    """
    Context wrapper for setting HTTP proxies.
    """

    proxies = []

    if http_proxy:
        proxies.append('http_proxy="%s"' % http_proxy)

    if https_proxy:
        proxies.append('https_proxy="%s"' % https_proxy)

    if proxies:
        proxies.insert(0, "export")
        cmd = " ".join(proxies)
        return prefix(cmd)

    return _DummyContext()

def virtualenv(virtualenv=None):
    """
    Context wrapper for activating Python virtual environments.
    """

    if virtualenv:
        cmd = "source %s" % os.path.join(virtualenv, "bin/activate")
        return prefix(cmd)

    return _DummyContext()
