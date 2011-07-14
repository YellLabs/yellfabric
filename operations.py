import os

import java, python

from fabric.api import local, env, require, cd, runs_once
from fabric.contrib.project import rsync_project

@runs_once
def fab_setup_paths():
    """
    Setup environment specific path variables under Fabric's `env`.
    """

    python.setup_paths()
    java.setup_paths()

def rsync_from_local():
    """
    Push a local checkout of the code to a remote machine.
    """

    require("tempdir", "project_path", "sudo_user")

    rsync_exclude = [ "*.pyc" ]
    rsync_opts = []

    if env.get("rsync_exclude"):
        rsync_exclude = rsync_exclude + env.rsync_exclude

    if env.sudo_user:
        rsync_opts = '--rsync-path="sudo -u %s rsync"' % env.sudo_user

    rsync_project(
        local_dir="%s/" % env.tempdir,
        remote_dir="%s/" % env.project_path,
        exclude=rsync_exclude,
        delete=True,
        extra_opts=rsync_opts)
