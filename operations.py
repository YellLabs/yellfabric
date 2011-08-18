import java
import python
import utils

import pprint

from fabric.api import env, require, runs_once
from fabric.utils import abort
from fabric.contrib.project import rsync_project


@runs_once
def fab_setup_paths():
    """
    Wrapper for setting up language dependent paths.
    """

    require("lang")

    if env.lang == "python":
        python.setup_paths()
    elif env.lang == "java":
        java.setup_paths()
    else:
        abort("Project language of %r unknown" % env.lang)


def scm_echo_info():

    require("scm_type")

    pprint.pprint(utils.scm_get_info(env.scm_type))


def rsync_from_local():
    """
    Push a local checkout of the code to a remote machine.
    """

    require("tempdir", "project_path", "sudo_user")

    rsync_exclude = ["*.pyc"]
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
