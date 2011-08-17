import glob
import os.path
import sys
import tempfile

from fabric.api import local, env, sudo, runs_once, require
from fabric.contrib.project import rsync_project

from utils import template_context, template_to_file
from fabric.operations import prompt


@runs_once
def setup_paths():
    require("java_root", "java_conf", "java_log", "project_name")

    env.war_file = "%s.war" % env.project_name
    env.war_path = os.path.join(env.java_root, env.war_file)
    env.app_config_archive = "%s-config.tar.gz" % env.project_name
    env.sql_archive = "%s-sql.tar.gz" % env.project_name
    env.app_config_dir = os.path.join(env.java_conf, env.project_name)
    env.log_dir = os.path.join(env.java_log, env.project_name)


@runs_once
def fetch_from_repo():
    # repo_base should be something like
    # http://cis-dev.local:8080/artifactory/libs-release-local/com/yelllabs
    prompt("Base URL for this project:", "repo_base")
    prompt("Version:", "proj_version")
    fetch = {}
    fetch[env.war_file] = \
        "%(repo_base)s/%(project_name)s/%(proj_version)s/" \
        "%(project_name)s-%(proj_version)s.war" % env
    fetch[env.app_config_archive] = \
        "%(repo_base)s/%(project_name)s/%(proj_version)s/" \
        "%(project_name)s-%(proj_version)s-config.tar.gz" % env
    fetch[env.sql_archive] = \
        "%(repo_base)s/%(project_name)s/%(proj_version)s/" \
        "%(project_name)s-%(proj_version)s-sql.tar.gz" % env
    for name, url in fetch.iteritems():
        local("wget -O%s '%s'" % (name, url))


@runs_once
def use_maven_build():
    require("war_path", provided_by="setup_paths")

    try:
        env.war_file = glob.glob("target/*.war")[0]
        env.app_config_archive = glob.glob("target/*-config.tar.gz")[0]
    except IndexError:
        sys.exit("Failed to find maven build products in target directory")


@runs_once
def render_settings_template():
    tempdir = tempfile.mkdtemp()
    local("tar -C'%s' -xzf '%s'" % (tempdir, env.app_config_archive))

    source_dir = os.path.join(tempdir, 'config')
    target_dir = os.path.join(tempdir, 'processed-config')

    os.mkdir(target_dir)
    context = template_context(env.settings_vars)

    for conf_file in os.listdir(source_dir):
        template_to_file(os.path.join(source_dir, conf_file),
                         os.path.join(target_dir, conf_file),
                         context)

    env.deploy_config_dir = target_dir


def rsync_as_user(remote_dir, local_dir, user, delete=False, exclude=()):
    extra_opts = '--rsync-path="sudo -u %s rsync"' % user
    rsync_project(
        remote_dir,
        local_dir,
        exclude=exclude,
        delete=delete,
        extra_opts=extra_opts,
    )


def deploy_java():
    render_settings_template()

    require("sudo_user")
    require("app_config_dir", "deploy_config_dir")
    rsync_as_user(
        "%s/" % env.app_config_dir,
        "%s/" % env.deploy_config_dir,
        env.sudo_user,
        delete=True,
    )
    require("war_file", "war_path")
    rsync_as_user(env.war_path, env.war_file, env.sudo_user)

    require("project_name")
    sudo(
        "/usr/local/sbin/deploy_tomcat_webapp.py %s" % env.project_name,
        shell=False,
    )
