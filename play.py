import os
import context_managers
import utils
import operations

from fabric.api import env, require, cd, runs_once, sudo, abort

@runs_once
def setup_paths():
    require("play_root", "project_name")

    env.project_path = os.path.join(env.play_root, env.project_name)
    env.config_source = os.path.join("conf", "application.conf.template")
    env.config_target = os.path.join("conf", "application.conf")


def sync_deps():
    """
    Download project dependencies and sync modules/lib dirs.
    """

    require(
        "project_path",
        "http_proxy",
        "https_proxy",
        "sudo_user",
    )
    with context_managers.proxy(env.http_proxy, env.https_proxy):
        utils.play_run(env.project_path, "dependencies --sync", user=env.sudo_user)


def restart():
    """
    Restart the application using supervisord.
    """

    require("project_name")

    cmd = "supervisorctl restart play-%s" % env.project_name
    sudo(cmd, shell=False)


@runs_once
def migratedb(command="apply"):
    """
    Perform database migrations using Evolutions.
    """

    require("project_path", "sudo_user")
    utils.play_run(env.project_path, "evolutions:%s" % command, user=env.sudo_user)


def deploy_play(ref=None, debug=False, dirty=False):
    """
    Standard Play deployment actions.
    """

    operations.fetch_render_copy(ref, debug, dirty, True)
    sync_deps()
    migratedb()
    restart()
