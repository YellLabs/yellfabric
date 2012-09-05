import glob
import os.path
import sys
import shutil
import tempfile

from fabric.api import local, env, sudo, runs_once, require
from fabric.contrib.project import rsync_project

from utils import template_context, template_to_file


@runs_once
def setup_paths():
    require("java_root", "java_conf", "java_log", "project_name")

    env.jar_file = "%s.jar" % env.project_name
    env.jar_path = os.path.join(env.jar_root, env.jar_file)

    env.war_file = "%s.war" % env.project_name
    env.war_path = os.path.join(env.java_root, env.war_file)

    env.app_config_archive = "%s-config.tar.gz" % env.project_name
    env.sql_archive = "%s-sql.tar.gz" % env.project_name

    try:
       env.config_dir_name
    except NameError:
       env.config_dir_name = None
    except AttributeError:
       env.config_dir_name = None

    if env.config_dir_name is None:
       env.config_dir_name = env.project_name
    env.app_config_dir = os.path.join(env.java_conf, env.config_dir_name)
    env.app_xml_config_dir = os.path.join(env.java_conf, env.project_name)
    env.log_dir = os.path.join(env.java_log, env.project_name)


@runs_once
def render_settings_template():
    non_template_exts = [".jks", ".pkcs12", ".pem", ".crt", ".cer"]

    tempdir = tempfile.mkdtemp()
    local("tar -C'%s' -xzf '%s'" % (tempdir, env.app_config_archive))

    source_dir = os.path.join(tempdir, 'config')
    target_dir = os.path.join(tempdir, 'processed-config')

    os.mkdir(target_dir)
    context = template_context(env.settings_vars)

    for conf_file in os.listdir(source_dir):
        file_name, file_extension = os.path.splitext(conf_file)
        if file_extension in non_template_exts:
            shutil.copy(os.path.join(source_dir, conf_file),
                         os.path.join(target_dir, conf_file))
        else:
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

    require("app_xml_config_dir", "deploy_config_dir")
    rsync_as_user(
        "%s/" % env.app_xml_config_dir,
        "%s/" % env.deploy_config_dir,
        env.sudo_user,
        delete=True
    )

    require("war_file", "war_path")
    rsync_as_user(env.war_path, env.war_file, env.sudo_user)

    require("project_name")
    if env.get("tomcat_context_path"):
        sudo(
            "/usr/local/sbin/deploy_tomcat_webapp.py %s --context %s" % (env.project_name, env.tomcat_context_path) ,
            shell=False,
        )
    else:
        sudo(
            "/usr/local/sbin/deploy_tomcat_webapp.py %s" % env.project_name ,
            shell=False,
        )

def deploy_jar():
    render_settings_template()

    require("sudo_user")
    require("app_config_dir", "deploy_config_dir")
    require("jar_file", "jar_path")
    require("project_name")

    rsync_as_user("%s/" % env.app_config_dir, "%s/" % env.deploy_config_dir, env.sudo_user, delete=True,)
    rsync_as_user(env.jar_path, env.jar_file, env.sudo_user)
