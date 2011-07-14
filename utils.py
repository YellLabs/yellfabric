"""
Generic utility classes for Fabric.

These should act as standalone functions and not modify Fabric's "env" directly.
"""

import context_managers

import os
import shutil
import tempfile

from fabric.api import run, sudo, local
from fabric.api import env, prompt, runs_once

def django_manage_run(virtualenv, path, cmd, user=None):
    """
    Run a Django management command from a Python virtual environment.

        - cmd: Management command to run.
    """

    manage_py = os.path.join(path, "manage.py")
    cmd = "python %s %s --noinput" % (manage_py, cmd)

    with context_managers.virtualenv(virtualenv):
        run_sudo_local(cmd, user)

def run_sudo_local(cmd, user=None):
    """
    Automagic wrapper for run(), sudo() and local() methods.

        - cmd: Command to execute.
        - user: User to execute commands as through sudo.

    Chooses the correct action based upon:
        - If the host is local then use local()
        - If a user is supplied then use sudo()
        - Otherwise use run()
    """

    if env.host_string in [ "localhost", "127.0.0.1" ]:
        local(cmd)
    elif user:
        sudo(cmd, user=user)
    else:
        run(cmd)

def scm_get_ref(scm_type):
    if env.has_key("scm_ref"):
        return env.scm_ref

    if scm_type in ["svn", "SVN"]:
        return "trunk"

    if scm_type in ["git", "GIT"]:
        return "dev"

@runs_once
def fetch_source(scm_type, scm_url, scm_ref=None, dirty=False):
    if dirty:
        tempdir = os.tempdir.dirname(os.tempdir.abstempdir(__file__))
    elif env.has_key("tempdir"):
        tempdir = env.tempdir
    else:
        tempdir = tempfile.mkdtemp()
        os.chmod(tempdir, 0755)

        if scm_type in [ "svn", "SVN" ]:
            if not scm_ref:
                scm_ref = "trunk"
            cmd = "svn checkout --quiet --config-option config:miscellany:use-commit-times=yes %s/%s %s" % (env.scm_url, scm_ref, tempdir)
        elif scm_type in [ "git", "GIT" ]:
            if not scm_ref:
                scm_ref = "dev"
            cmd = "git clone -b %s %s %s" % (scm_ref, env.scm_url, tempdir)

        local(cmd)

    return tempdir

def delete_source(tempdir, dirty=False):
    if dirty:
        return

    if env.host != env.hosts[-1]:
        return

    shutil.rmtree(tempdir)

@runs_once
def template_context(vars):
    """
    Compiles a list of variables and their values from Fabric's env into a
    dictionary which can be used to render a template. Any values that aren't
    present in env are prompted for.
    """

    context = {}
    for var in vars:
        context[var] = env.get(var) or prompt('Enter settings var for %r:' % var)

    return context

def template_to_file(source, target, context):
    """
    Populate templated local_settings and place it in the tempdir to be rsynced.
    """

    with open(target, "w") as target_file:
        with open(source) as source_file:
            text = source_file.read() % context
        target_file.write(text)
