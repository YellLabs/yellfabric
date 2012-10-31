import os
import context_managers
import utils
import operations

from fabric.api import env, require, cd, runs_once, sudo, abort, local, lcd

def create_custom_command():
    """
    Creates a custom build command executed in operations.fetch_render_copy
    """
    def build_cmd(tempdir):
        package_dist()
        extract_project()
    return build_cmd


def extract_project(zip_bin="unzip"):
    """
    Extracts the archive created by `play dist`.

    The resulting lib/ directory contains all project code and deps.
    """

    require("project_name", "project_version", "tempdir")
    with lcd(os.path.join(env.tempdir,"dist")):
        local("%s %s-%s.zip" % (zip_bin, env.project_name, env.project_version))


def package_dist():
    """
    Runs `play dist` to produce a zip file with all project dependencies.

    Assumes play_bin is the play 2 binary.
    """

    require("play2_bin", "tempdir")
    with lcd(env.tempdir):
        local("%s dist" % (env.play2_bin))


@runs_once
def setup_paths():
    require("play2_root", "project_name")

    env.project_path = os.path.join(env.play2_root, env.project_name)
    env.config_source = os.path.join("conf", "application.conf.template")
    env.config_target = os.path.join("conf", "application.conf")


def tail(stderr=False):
    """
    Tail the output of an application using supervisord.

    stderr argument can be supplied to return STDERR instead of STDOUT.
    """

    require("project_name")

    cmd = "supervisorctl tail play2-%s" % env.project_name

    if stderr:
        cmd += " stderr"

    sudo(cmd, shell=False)


def status():
    """
    Query the status of an application using supervisord.
    """

    require("project_name")

    cmd = "supervisorctl status play2-%s" % env.project_name
    sudo(cmd, shell=False)


def restart():
    """
    Restart the application using supervisord.
    """

    require("project_name")

    cmd = "supervisorctl restart play2-%s" % env.project_name
    sudo(cmd, shell=False)


def start_play():
    """
    Start the play application.
    """

    require("project_name")

    cmd = "supervisorctl start play2-%s" % env.project_name
    sudo(cmd, shell=False)

    
def stop_play():
    """
    Stop the currently running play application.
    """

    require("project_name")

    cmd = "supervisorctl stop play2-%s" % env.project_name
    sudo(cmd, shell=False)

def deploy_play2(ref=None, debug=False, dirty=False, dist=False):
    """
    Standard Play 2 deployment actions.
    """

    require("project_name", "project_version")
    if dist:
        require("play2_bin")

    build_cmd = create_custom_command()
    local_build_path = os.path.join("dist", ''.join([env.project_name, '-', env.project_version, os.sep]))
    operations.fetch_render_copy(ref, debug, dirty, True, build_cmd, local_build_path)
    restart()
