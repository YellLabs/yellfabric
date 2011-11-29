import os
import context_managers
import utils
import operations

from fabric.api import env, require, cd, runs_once, sudo, abort

@runs_once
def setup_paths():
    require("play_root", "project_name")

    env.project_path = os.path.join(env.play_root, env.project_name)


def sync_deps():
    """
    """

    require(
        "project_path",
        "http_proxy",
        "https_proxy",
        "sudo_user",
    )
    with context_managers.proxy(env.http_proxy, env.https_proxy):
        utils.play_run(env.project_path, "dependencies --sync", user=env.sudo_user)


def render_settings_template():
    """
    Render a settings file from a template in a local checkout.
    """

    require("tempdir", "project_path", "settings_vars")

    source = os.path.join(env.tempdir, "conf", "application.conf.template")
    target = os.path.join(env.tempdir, "conf", "application.conf")
    context = utils.template_context(env.settings_vars)

    utils.template_to_file(source, target, context)


def restart():
    """
    """

    require("project_name")

    cmd = "supervisorctl restart play-%s" % env.project_name
    sudo(cmd, shell=False)


@runs_once
def migratedb():
    """
    """

    require("project_path", "sudo_user")
    utils.play_run(env.project_path, "evolutions:apply", user=env.sudo_user)


def fetch_render_copy(ref=None, debug=False, dirty=False, copy_remote=False):
    """
    Fetch source code, render settings file, push remotely and delete checkout.
    """

    require("scm_type", "scm_url")

    env.tempdir = utils.fetch_source(env.scm_type, env.scm_url, ref, dirty)
    render_settings_template()

    if copy_remote:
        operations.rsync_from_local()

    utils.delete_source(env.tempdir, dirty)


def deploy_play(ref=None, debug=False, dirty=False):
    """
    Standard Play deployment actions.
    """

    fetch_render_copy(ref, debug, dirty, True)
    sync_deps()
    migratedb()
    restart()
