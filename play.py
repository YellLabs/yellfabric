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


def tail(stderr=False):
    """
    Tail the output of an application using supervisord.

    stderr argument can be supplied to return STDERR instead of STDOUT.
    """

    require("project_name")

    cmd = "supervisorctl tail play-%s" % env.project_name

    if stderr:
        cmd += " stderr"

    sudo(cmd, shell=False)


def status():
    """
    Query the status of an application using supervisord.
    """

    require("project_name")

    cmd = "supervisorctl status play-%s" % env.project_name
    sudo(cmd, shell=False)


def restart():
    """
    Restart the application using supervisord.
    """

    require("project_name")

    cmd = "supervisorctl restart play-%s" % env.project_name
    sudo(cmd, shell=False)


def start_play():
    """
    Start the play application.
    """

    require("project_name")

    cmd = "supervisorctl start play-%s" % env.project_name
    sudo(cmd, shell=False)

    
def stop_play():
    """
    Stop the currently running play application.
    """

    require("project_name")

    cmd = "supervisorctl stop play-%s" % env.project_name
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


def dirty_play_test(ref=None, debug=False, dirty=True):
    """
    Deploy LOCAL code and start app in test mode
    """

    require("project_name","sudo_user")

    operations.fetch_render_copy(ref, debug, dirty, True)
    sync_deps()
    # migratedb() should not be required as new db created for tests
    stop_play()

    utils.play_run(env.project_path, "test -XX:CompileCommand=exclude,jregex/Pretokenizer,next" , user=env.sudo_user)


def dirty_play_autotest(ref=None, debug=False, dirty=True):
    """
    Deploy LOCAL code and run automatic tests
    """

    require("project_name","sudo_user")

    operations.fetch_render_copy(ref, debug, dirty, True)
    sync_deps()
    # migratedb() should not be required as new db created for tests
    stop_play()

    utils.play_run(env.project_path, "autotest -XX:CompileCommand=exclude,jregex/Pretokenizer,next" , user=env.sudo_user)
    # restart app in prod mode afterwards
    start_play()
