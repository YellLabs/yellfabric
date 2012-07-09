import java
import python
import glassfish
import play
import static
import utils

import os.path
import pprint
import glob

from fabric.api import env, require, runs_once, local
from fabric.utils import abort
from fabric.contrib.project import rsync_project
from fabric.operations import prompt


@runs_once
def fab_setup_paths():
    """
    Wrapper for setting up language dependent paths.
    """

    require("lang")

    if env.lang in ["django", "python"]:
        python.setup_paths()
    elif env.lang in ["tomcat", "java"]:
        java.setup_paths()
    elif env.lang == "glassfish":
        glassfish.setup_paths()
    elif env.lang == "play":
        play.setup_paths()
    elif env.lang == "static":
        static.setup_paths()
    else:
        abort("Project language %r unknown" % env.lang)


def scm_echo_info():

    require("scm_type")

    pprint.pprint(utils.scm_get_info(env.scm_type))


def rsync_from_local():
    """
    Push a local checkout of the code to a remote machine.
    """

    require("tempdir", "project_path", "sudo_user")

    rsync_exclude = ["*.pyc"]
    rsync_opts = []

    if env.get("rsync_exclude"):
        rsync_exclude = rsync_exclude + env.rsync_exclude

    if env.sudo_user:
        rsync_opts = '--rsync-path="sudo -u %s rsync"' % env.sudo_user

    rsync_project(
        local_dir="%s/" % env.tempdir,
        remote_dir="%s/" % env.project_path,
        exclude=rsync_exclude,
        delete=True,
        extra_opts=rsync_opts)


@runs_once
def use_maven_build():
    require("war_path", provided_by="setup_paths")

    try:
        env.war_file = glob.glob("target/*.war")[0]
        env.app_config_archive = glob.glob("target/*-config.tar.gz")[0]
    except IndexError:
         sys.exit("Failed to find maven build products in target directory")


@runs_once
def fetch_from_repo():
    # repo_base should be something like
    # http://cis-dev.local:8080/artifactory/libs-release-local/com/yelllabs
    require("project_name")
    prompt("Base URL for this project:", "repo_base")
    prompt("Version:", "proj_version")
    fetch = {}
    fetch[env.war_file] = \
        "%(repo_base)s/%(project_name)s/%(proj_version)s/" \
        "%(project_name)s-%(proj_version)s.war" % env
    fetch[env.app_config_archive] = \
        "%(repo_base)s/%(project_name)s/%(proj_version)s/" \
        "%(project_name)s-%(proj_version)s-config.tar.gz" % env
    if env.get('has_sql_archive'):
        fetch[env.sql_archive] = \
            "%(repo_base)s/%(project_name)s/%(proj_version)s/" \
            "%(project_name)s-%(proj_version)s-sql.tar.gz" % env
    for name, url in fetch.iteritems():
        local("wget -O%s '%s'" % (name, url))


def fetch_render_copy(ref=None, debug=False, dirty=False, copy_remote=False):
    """
    Fetch source code, render settings file, push remotely and delete checkout.

    env.custom_config_files can be optionally used to specify key-value pairs
    of config templates to be processed. The structure looks like:

    env.custom_config_files = [
        { "source": "conf/foo.conf.template", "dest": "conf/foo.conf" },
        { "source": "conf/bar.conf.template", "dest": "conf/bar.conf" }
    ]
    """

    require("scm_type", "scm_url", "config_source", "config_target", "settings_vars")

    env.tempdir = utils.fetch_source(env.scm_type, env.scm_url, ref, dirty)
    config_source = os.path.join(env.tempdir, env.config_source)
    config_target = os.path.join(env.tempdir, env.config_target)
    utils.render_settings_template(config_source, config_target, env.settings_vars, debug)

    # Additional config templates are optional.
    if "custom_config_files" in env:
        for custom_config_file in env.custom_config_files:
            try:
                config_source = os.path.join(env.tempdir, custom_config_file['source'])
                config_target = os.path.join(env.tempdir, custom_config_file['dest'])
                utils.render_settings_template(config_source, config_target, env.settings_vars, debug)
            except KeyError:
                # Blow up if the structure isn't as expected.
                abort("The structure of env.custom_config_files is invalid")

    if copy_remote:
        rsync_from_local()

    utils.delete_source_conditional(env.tempdir, dirty)
