import os
import operations
import utils
from shutil import copy

from fabric.api import env, require, runs_once, sudo, local, lcd, abort

def create_custom_command(dist):
    """
    Creates a custom build command executed in operations.fetch_render_copy
    """
    def build_cmd(tempdir):
        if dist is True:
            package_dist()
            extract_project()
        else:
            stage_project()
    return build_cmd

def stage_project():
    # Follows best practice as of http://www.playframework.com/documentation/2.0/Production
    require("play2_bin", "tempdir")
    with lcd(env.tempdir):
        local("%s clean compile stage" % (env.play2_bin))

def extract_project(zip_bin="unzip"):
    """
    Extracts the archive created by `play dist`.

    The resulting lib/ directory contains all project code and deps.
    """

    require("project_name", "project_version", "tempdir")
    with lcd(os.path.join(env.tempdir,"dist")):
        local("%s %s-%s.zip" % (zip_bin, env.project_name, env.project_version))
        
        # adding the version file to the folder rsynced with server
        version_file_dir = os.path.join(env.tempdir, "dist/%s-%s" % (env.project_name, env.project_version))

        src = "%s/version" % env.tempdir
        dst = "%s/version" % version_file_dir
        copy(src, dst)


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

    # If 'stderr' is supplied via command line, check its validity
    if stderr == 'True':
        stderr = True
    if stderr == 'False':
        stderr = False
    # If we've failed to produce a boolean flag, abort
    if stderr is not True and stderr is not False:
        abort('stderr argument must equal True or False')

    cmd += " stderr" if stderr else " stdout"

    sudo(cmd, shell=False)


def status():
    """
    Query the status of an application using supervisord.
    """

    require("project_name")

    utils.supervisorctl("status", "play2-%s" % env.project_name)


def restart():
    """
    Restart the application using supervisord.
    """

    require("project_name")

    utils.supervisorctl("restart", "play2-%s" % env.project_name)


def start_play():
    """
    Start the play application.
    """

    require("project_name")

    utils.supervisorctl("start", "play2-%s" % env.project_name)

    
def stop_play():
    """
    Stop the currently running play application.
    """

    require("project_name")

    utils.supervisorctl("stop", "play2-%s" % env.project_name)

def deploy_play2(ref=None, debug=False, dirty=False, dist=False):
    """
    Standard Play 2 deployment actions.
    """

    # If 'dist' is supplied via command line, check its validity
    if dist == 'True':
        dist = True
    if dist == 'False':
        dist = False
    # If we've failed to produce a boolean flag, abort
    if dist is not True and dist is not False:
        abort('dist argument must equal True or False')

    require("project_name", "project_version")
    build_cmd = create_custom_command(dist)

    local_build_path= ""
    if dist:
        local_build_path = os.path.join("dist",
                                        ''.join([env.project_name,
                                        '-', env.project_version, os.sep]))

    operations.fetch_render_copy(ref, debug, dirty, True,
                                     build_cmd, local_build_path)
    restart()
