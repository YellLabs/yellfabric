import os
from fabric.api import run, sudo, prefix, env

class DummyContext():
    """
    Dummy context object that can be returned in the event that no prefix()
    context object is required.
    """

    def __init__(self):
        pass
    def __enter__(self):
        pass
    def __exit__(self):
        pass

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
        command = " ".join(["export"] + proxies)
        return prefix(command)

    return DummyContext()
