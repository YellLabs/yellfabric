import os

import java, python, glassfish_java

from fabric.api import local, env, require, cd, runs_once
from fabric.utils import abort
from fabric.contrib.project import rsync_project

@runs_once
def fab_setup_paths():
    """
    Wrapper for setting up language dependent paths.
    """

    require("lang")

    if env.lang in ["django", "python"]:
        python.setup_paths()
    elif env.lang in ["tomcat", "java"]:
        java.setup_paths()
    elif env.lang == "glassfish":
        glassfish_java.setup_paths()
    else:
        abort("Project language %r unknown" % env.lang)

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
