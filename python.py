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
        os.path.join(env.project_path, "deploy", "*.wsgi")
    env.config_source = "local_settings.py.template"
    env.config_target = "local_settings.py"


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
    if env.get("packages_url") is not None:
        cmd += " -f %s" % env.get("packages_url")

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
    cmd = "touch -c %s" % env.wsgi_path
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
def migratedb(rollback=False):
    """
    Perform 'migrate' action for a Django project.
    """

    require("virtualenv_path", "project_path", "sudo_user")

    #
    # Some things need to be done first (i.e. if they need a different
    # database connection or some custom args)
    #
    if "migratedb_first" in env:

        for app, args in env.migratedb_first.iteritems():

            version = get_south_migrate_version(app, rollback)

            migrate_app_db(app, version, args)

    #
    # Do the rest afterwards
    #
    if has_version_info():

        apps = env.south_migrations.keys()

        for app in apps:

            print app

            version = get_south_migrate_version(app, rollback)

            migrate_app_db(app, version)

    #
    # If we know nothing, just migrate everything
    #
    else:
        migrate_app_db()


def migrate_app_db(app=None, version=None, args=None):

    require("virtualenv_path", "project_path", "sudo_user")

    if app:
        if args:
            command = ' '.join(['migrate', app, version, args])
        else:
            command = ' '.join(['migrate', app, version])
    else:
        command = "migrate"

    print command

    utils.django_manage_run(
        env.virtualenv_path,
        env.project_path,
        command,
        env.sudo_user,
    )


def get_south_migrate_version(app, rollback=False):

    version = None if rollback else "auto"

    if has_version_info():

        if app in env.south_migrations:

            if rollback:
                version = env.south_migrations[app]["rollback"]

            else:
                version = env.south_migrations[app]["deploy"]

    return version


def has_version_info():

    if "south_migrations" in env:
        if "scm_tag" in env:
            return True

    return False


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


def deploy_django(ref=None, debug=False, dirty=False):
    """
    Standard Django deployment actions.
    """

    create_virtualenv()
    operations.fetch_render_copy(ref, debug, dirty, True)
    pip_requirements()
    migratedb()
    refresh_wsgi()


def rollback_django(ref=None, debug=False, dirty=False):
    """
    There is nothing standard about rolling back.
    """
    if has_version_info():
        #
        # To roll back we need to fetch the existing version, execute the
        # database rollback, and then do a deploy of a specific version
        #
        create_virtualenv()

        # Copy the new code... the one we want to back out, as we need the
        # migrations from this
        fetch_render_copy(ref, debug, dirty)

        # Rollback the database
        migratedb(True)

        # Get the old code
        del env['tempdir']
        fetch_render_copy(env.scm_tag["rollback"], debug, dirty, True)

        pip_requirements()
        refresh_wsgi()

    else:
        abort("No version info present to allow rollback")
