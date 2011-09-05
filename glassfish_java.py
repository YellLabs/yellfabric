import glob
import os.path
import shutil
import sys
import tempfile

from fabric.api import local, env, sudo, lcd, run, runs_once, require
from fabric.contrib.project import rsync_project

from utils import template_context, template_to_file
from fabric.operations import prompt

@runs_once
def setup_paths():
    require("java_root", "java_conf", "java_log", "project_name", "config_dir_name")

    env.war_file = "%s.war" % env.project_name
    env.war_path = os.path.join(env.java_root, env.war_file)
    env.app_config_archive = "%s-config.tar.gz" % env.project_name
    env.app_config_dir = os.path.join(env.java_conf, env.config_dir_name)
    env.log_dir = os.path.join(env.java_log, env.project_name)
    env.asadmin = "/opt/glassfish/bin/asadmin --terse"

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

    # Need to copy target_dir/etc and it's subdirectories to /etc/ for
    # the application configuration
    #shutil.copytree(os.path.join(target_dir, "etc"), "/etc")

    env.deploy_config_dir = target_dir

def rsync_as_user(remote_dir, local_dir, user, delete = False, exclude = ()):
    extra_opts = '--rsync-path="sudo -u %s rsync"' % user
    rsync_project(remote_dir, local_dir, exclude = exclude, delete = delete, extra_opts = extra_opts)

def _check_call(*popenargs, **kwargs):
    """
    EL5 ships with Python 2.4 which doesn't have subprocess.check_call()
    Back ported from Python 2.6.6
    """

    retcode = subprocess.call(*popenargs, **kwargs)
    cmd = kwargs.get("args")
    if cmd is None:
        cmd = popenargs[0]
    if retcode:
        raise CalledProcessError(retcode, cmd)
    return retcode

def glassfish_service(action):
    """
    Stop or restart Glassfish
    """

    require("asadmin")
    run("%s domain1" % (env.asadmin, action))

def undeploy(application):
    """
    Undeploy the application
    """
    
    require("asadmin")
    applications = run("%s list-applications" % env.asadmin).split("\n")
    applications = [x.split()[0] for x in applications]

    if application in applications:
        run("%s undeploy %s" % (env.asadmin, application))

def deploy(context, war):
    """
    deploy the application
    """

    require("asadmin")
    run("%s deploy %s" % (env.asadmin, war))

def deploy_resources(resource_file):
    """
    deploy the resources
    """

    require("asadmin")
    run("%s add-resources %s" % (env.asadmin, resource_file))

def undeploy_jdbc_connection_pool_resource(jndi_name):
    """
    undeploy the jdbc connection pool
    """

    require("asadmin")
    connection_pools = run("%s list-jdbc-connection-pools" % env.asadmin).split("\n")

    if jndi_name in connection_pools:
        run("%s delete-jdbc-connection-pool --cascade true %s" % (env.asadmin, jndi_name))

def undeploy_mail_resource(jndi_name):
    """
    undeploy the mail resource
    """

    require("asadmin")
    mail_resources = run("%s list-javamail-resources" % env.asadmin).split("\n")

    if jndi_name in mail_resources:
        run("%s delete-javamail-resource %s" % (env.asadmin, jndi_name))

def deploy_java():
    render_settings_template()
    
    require("sudo_user")
    require("app_config_dir", "deploy_config_dir")
    rsync_as_user("%s/" % env.app_config_dir, "%s/" % env.deploy_config_dir, env.sudo_user, delete = True)

    require("war_file", "war_path")
    rsync_as_user(env.war_path, env.war_file, env.sudo_user)
    
    require("java_root", "project_name")
    remote_war_file=os.path.join(env.java_root, "%s.war" % env.project_name)

    undeploy(env.project_name)

    if env.jdbc_cp_jndi_name:
        undeploy_jdbc_connection_pool_resource(env.jdbc_cp_jndi_name)

    if env.mail_resource_jndi_name:
        undeploy_mail_resource(env.mail_resource_jndi_name)

    require("java_conf")
    if env.resources_to_deploy:
        resource_file=os.path.join(env.java_conf, env.config_dir_name, "glassfish-resources.xml")
        deploy_resources(resource_file)

    deploy(env.project_name, remote_war_file)
