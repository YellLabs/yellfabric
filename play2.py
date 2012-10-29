import os
import context_managers
import utils
import operations

from fabric.api import env, require, cd, runs_once, sudo, abort, local, lcd

def create_custom_command(play_bin, zip_bin="unzip"):
    """
    Packages the project using `play dist` and unzips the resulting file.

    The lib/ directory contains all project code and deps.

    Assumes play_bin is the play 2 binary.

    Resulting function takes a 'tempdir' arg to match the definition in static.py
    """

    require("project_name", "project_version")
    def local_build_command(tempdir):
        with lcd(tempdir):
            local("%s dist" % (play_bin))
            with lcd("dist"):
                local("%s %s-%s.zip" % (zip_bin, env.project_name, env.project_version))
    return local_build_command


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

def deploy_play2(ref=None, debug=False, dirty=False):
    """
    Standard Play 2 deployment actions.
    """

    require("project_name", "project_version", "play2_bin")
    build_cmd = create_custom_command(env.play2_bin)
    local_build_path = os.path.join("dist/", ''.join([env.project_name, '-', env.project_version]))
    operations.fetch_render_copy(ref, debug, dirty, True, build_cmd, local_build_path)
    restart()
