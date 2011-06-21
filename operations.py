import os

from fabric.api import local, env, require, cd, runs_once
from fabric.contrib.project import rsync_project

def fab_setup_paths():
    """
    Setup environment specific path variables under Fabric's `env`.
    """

    require("root", "vhost", "project_name")

    env.vhost_path = os.path.join(env.root, env.vhost)
    env.project_path = os.path.join(env.vhost_path, env.project_name)
    env.virtualenv_path = os.path.join(env.vhost_path, "%s-env" % env.project_name)
    env.requirements_path = os.path.join(env.project_path, "requirements", "project.txt")
    env.wsgi_path = os.path.join(env.project_path, "deploy", "%s.wsgi" % env.project_name)

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
