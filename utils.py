"""
Generic utility classes for Fabric.

These should act as standalone functions and not modify Fabric's "env" directly.
"""

import context_managers

import os
import shutil
import tempfile

from fabric.api import env, prompt, runs_once, sudo, local, puts, lcd

def django_manage_run(virtualenv, path, cmd, user, flag="--noinput"):
    """
    Run a Django management command from a Python virtual environment.

        - cmd: Management command to run.
    """

    manage_py = os.path.join(path, "manage.py")
    cmd = "python %s %s %s" % (manage_py, cmd, flag)

    with context_managers.virtualenv(virtualenv):
        sudo(cmd, user=user)

@runs_once
def scm_get_ref(scm_type):
    if scm_type.lower() == "svn":
        puts("SCM reference must be a 'path' relative to the project's root URL.")
        default = "trunk"
    elif scm_type.lower() == "git":
        puts("SCM reference must be a named 'branch', 'tag' or 'revision'.")
        default = "master"

    ref = prompt("SCM ref", default=default)
    return ref

@runs_once
def fetch_source(scm_type, scm_url, scm_ref=None, dirty=False):
    if dirty:
        tempdir = os.tempdir.dirname(os.tempdir.abstempdir(__file__))
    elif env.has_key("tempdir"):
        tempdir = env.tempdir
    else:
        tempdir = tempfile.mkdtemp()
        os.chmod(tempdir, 0755)

        if not scm_ref:
            scm_ref = scm_get_ref(scm_type)

        if scm_type.lower() == "svn":
            cmd = "svn checkout --quiet --config-option config:miscellany:use-commit-times=yes %s/%s %s" % (env.scm_url, scm_ref, tempdir)
        elif scm_type.lower() == "git":
            cmd = "git clone %s %s" % (env.scm_url, tempdir)

        local(cmd)

        if scm_type.lower() == "git":
            with lcd(tempdir):
                local("git checkout -b %s %s" % (scm_ref, scm_ref))

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
