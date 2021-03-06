import java
import python
import glassfish
import play
import play2
import static
import utils

import csv
import os.path
import pprint
import glob
import json

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
    elif env.lang == "play2":
        play2.setup_paths()
    elif env.lang == "static":
        static.setup_paths()
    else:
        abort("Project language %r unknown" % env.lang)


def scm_echo_info():

    require("scm_type")

    pprint.pprint(utils.scm_get_info(env.scm_type))


def rsync_from_local(local_path):
    """
    Push a local checkout of the code to a remote machine.

    local_subdir specifies the subdirectory of the project to be
    synced (e.g. build/).
    """

    require("tempdir", "project_path", "sudo_user")

    rsync_exclude = ["*.pyc"]
    rsync_opts = []

    if env.get("rsync_exclude"):
        rsync_exclude = rsync_exclude + env.rsync_exclude

    if env.sudo_user:
        rsync_opts = '--rsync-path="sudo -u %s rsync"' % env.sudo_user

    rsync_project(
        local_dir=os.path.join(env.tempdir, local_path),
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
        abort("Failed to find maven build products in target directory")


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


def fetch_render_copy(ref=None, debug=False, dirty=False, copy_remote=False,
                      build_local_cmd=None, local_path=""):
    """
    Fetch source code, render settings file, push remotely and delete checkout.
    """

    require("scm_type", "scm_url", "config_source", "config_target", "settings_vars")

    env.tempdir = utils.fetch_source(env.scm_type, env.scm_url, ref, dirty)
    config_source = os.path.join(env.tempdir, env.config_source)
    config_target = os.path.join(env.tempdir, env.config_target)

    utils.render_settings_template(config_source, config_target, env.settings_vars, debug)
    
    utils.render_custom_templates(env.tempdir, env.settings_vars, debug)

    # Don't try to handle any errors here - the deploy should fail.
    if build_local_cmd:
        build_local_cmd(env.tempdir)

    if copy_remote:
        rsync_from_local(local_path)

    utils.delete_source_conditional(env.tempdir, dirty)


def render_ci_props(scm_type="git"):
    """
    output ci-build properties to a file called ci_props.json in current workspace
    """

    build_number = os.environ.get("BUILD_NUMBER")
    job_name = os.environ.get("JOB_NAME")
    jenkins_url = os.environ.get("JENKINS_URL")
    job_url = os.environ.get("JOB_URL")
    scm_type = scm_type.lower()

    if(scm_type == "git"):
        scm_revision = os.environ.get("GIT_COMMIT")
        scm_branch = os.environ.get("GIT_BRANCH")
    if(scm_type == "svn"):
        scm_revision = os.environ.get("SVN_REVISION")
        scm_branch = os.environ.get("SVN_BRANCH")
    
    build_props = {}
    build_props['name']=env.project_name
    build_props['status']='ok'
    if(env.get("project_version")==None):
        build_props['version']="project_version not defined in fabfile.py"
    else:
        build_props['version']=env.project_version

    build_props['buildNumber']=build_number
    build_props['jobName']=job_name
    build_props['jobUrl']=job_url
    build_props['jenkinsUrl']=jenkins_url
    build_props['sourceControlSystem']=scm_type
    build_props['sourceControlRevision']=scm_revision
    build_props['sourceControlBranch']=scm_branch

    json_props = json.dumps(build_props)

    build_props_file = open("ci_props.json", "w")
    build_props_file.write(json_props)



def render_settings_template(debug=False):
    """
    Render settings files - parameters will be set based upon parms in fabfile
    """
    utils.render_settings_template(env.config_source, env.config_target, env.settings_vars, debug)
    
    utils.render_custom_templates(".", env.settings_vars, debug)
                

def load_extdata(filename):
    """
    Populate env.extdata as a dictionary of Puppet's extlookup/extdata
    key+value entries for later use by extlookup().

    Takes a single CSV file as a mandatory argument.
    """

    filename = os.path.expanduser(filename)
    if not os.path.exists(filename):
        abort("File %r not found" % filename)

    extdata = csv.reader(open(filename))
    env.extdata = {}

    for row in extdata:
        if len(row) < 1:
            continue

        env.extdata[row[0]] = row[1:]


def extlookup(key):
    """
    Lookup a password from by Puppet's extlookup/extdata store.
    This requires that env.extdata has been populated by load_extdata()

    Currently returns a single value that is only suitable for passwords.
    """

    require("extdata", provided_by="load_extdata")

    value = env.extdata.get(key, [])

    if len(value) != 1:
        abort("Could not extlookup single value for key %r" % key)

    return value[0]
