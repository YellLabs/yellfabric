import os
import context_managers
import utils
import operations

from fabric.api import env, require, cd, runs_once, sudo, abort


@runs_once
def setup_paths():
    require("python_root", "project_name", "vhost")

    env.vhost_path = os.path.join(env.python_root, env.vhost)
    env.project_path = os.path.join(env.vhost_path, env.project_name)
    env.virtualenv_path = \
        os.path.join(env.vhost_path, "%s-env" % env.project_name)
    env.requirements_path = \
        os.path.join(env.project_path, "requirements", "project.txt")
    env.wsgi_path = \
        os.path.join(env.project_path, "deploy", "%s.wsgi" % env.project_name)


def create_virtualenv():
    """
    Create a Python virtual environment.
    """

    require(
        "virtualenv_path",
        "python_bin",
        "http_proxy",
        "https_proxy",
        "sudo_user",
    )
    cmd = "virtualenv --python %s %s" % (env.python_bin, env.virtualenv_path)

    with context_managers.proxy(env.http_proxy, env.https_proxy):
        # Needs to cd into a directory that the sudo user can temporarily write
        # to.
        with cd("/tmp"):
            sudo(cmd, user=env.sudo_user)


def pip_requirements():
    """
    Install project requirements using PIP into a Python virtual environment.
    """

    require(
        "virtualenv_path",
        "requirements_path",
        "http_proxy",
        "https_proxy",
        "sudo_user",
    )
    cmd = "pip install --quiet --requirement %s" % env.requirements_path

    # append packages url if specified
    packages_url = env.packages_url
    if packages_url is not None:
        cmd += " -f %s" % packages_url

    with context_managers.proxy(env.http_proxy, env.https_proxy):
        with context_managers.virtualenv(env.virtualenv_path):
            sudo(cmd, user=env.sudo_user)


def render_settings_template(debug=False):
    """
    Render a settings file from a template in a local checkout.
    """

    require("tempdir", "project_path", "settings_vars")

    source = os.path.join(env.tempdir, "local_settings.py.template")
    target = os.path.join(env.tempdir, "local_settings.py")
    context = utils.template_context(env.settings_vars)

    # Treat as a string even though it's going to be rendered as unquoted.
    # Clobbers anything from env in the project's own fabfile because the
    # default should always be False.
    if "%s" % debug in ["True", "False"]:
        context["DEBUG"] = debug
    else:
        abort("local_settings.DEBUG may only be True or False")

    utils.template_to_file(source, target, context)


def refresh_wsgi():
    """
    Touch a WSGI file so that Apache w/mod_wsgi reloads a project.
    """

    require("wsgi_path", "sudo_user")
    cmd = "touch %s" % env.wsgi_path
    sudo(cmd, user=env.sudo_user)


@runs_once
def syncdb():
    """
    Perform 'syncdb' action for a Django project.
    """

    require("virtualenv_path", "project_path", "sudo_user")
    utils.django_manage_run(
        env.virtualenv_path,
        env.project_path,
        "syncdb",
        env.sudo_user,
    )


@runs_once
def migratedb():
    """
    Perform 'migrate' action for a Django project.
    """

    require("virtualenv_path", "project_path", "sudo_user")

    if "migratedb_first" in env:
        for app, args in env.migratedb_first.iteritems():
            utils.django_manage_run(
                env.virtualenv_path,
                env.project_path,
                ' '.join(['migrate', app, args]),
                env.sudo_user,
            )

    utils.django_manage_run(
        env.virtualenv_path,
        env.project_path,
        "migrate",
        env.sudo_user,
    )


@runs_once
def create_superuser(username=None, email=None):
    """
    Create a django superuser
    """

    require("virtualenv_path", "project_path", "sudo_user")
    cmd = "createsuperuser"

    if username:
        cmd = "%s --username=%s" % (cmd, username)

    if email:
        cmd = "%s --email=%s" % (cmd, email)

    utils.django_manage_run(
        env.virtualenv_path,
        env.project_path,
        cmd,
        env.sudo_user,
        interactive=True,
    )


def fetch_render_copy(ref=None, debug=False, dirty=False):
    """
    Fetch source code, render settings file, push remotely and delete checkout.
    """

    require("scm_type", "scm_url")

    env.tempdir = utils.fetch_source(env.scm_type, env.scm_url, ref, dirty)
    render_settings_template(debug)
    operations.rsync_from_local()
    utils.delete_source(env.tempdir)


def deploy_django(ref=None, debug=False, dirty=False):
    """
    Standard Django deployment actions.
    """

    create_virtualenv()
    fetch_render_copy(ref, debug, dirty)
    pip_requirements()
    migratedb()
    refresh_wsgi()
