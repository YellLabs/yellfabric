import glob
import os.path
import shutil
import sys
import tempfile

from fabric.api import local, env, sudo, lcd, run, runs_once, require
from fabric.contrib.project import rsync_project

from utils import template_context, template_to_file
from fabric.operations import prompt

PATH_YELL_WEBAPPS=os.path.join("/", "usr", "share", "java", "wars")
PATH_YELL_CONF=os.path.join("/", "etc", "yell")

@runs_once
def setup_paths():
    require("java_root", "java_conf", "java_log", "project_name", "config_dir_name")

    env.war_file = "%s.war" % env.project_name
    env.war_path = os.path.join(env.java_root, env.war_file)
    env.app_config_archive = "%s-config.tar.gz" % env.project_name
    env.app_config_dir = os.path.join(env.java_conf, env.config_dir_name)
    env.log_dir = os.path.join(env.java_log, env.project_name)

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

    run("/opt/glassfish/bin/asadmin %s domain1" % action)

def undeploy(application):
    """
    Undeploy the application
    """
    
    applications = run("/opt/glassfish/bin/asadmin list-applications")

    if applications.__contains__(application):
        run("/opt/glassfish/bin/asadmin undeploy %s" % application)

def deploy(context, war):
    """
    deploy the application
    """

    run("/opt/glassfish/bin/asadmin deploy %s" % war)

def deploy_resources(resource_file):
    """
    deploy the resources
    """

    run("/opt/glassfish/bin/asadmin add-resources %s" % resource_file)

def undeploy_jdbc_connection_pool_resource(jndi_name):
    """
    undeploy the jdbc connection pool
    """
    connection_pools = run("/opt/glassfish/bin/asadmin list-jdbc-connection-pools")

    if connection_pools.__contains__(jndi_name):
        run("/opt/glassfish/bin/asadmin delete-jdbc-connection-pool --cascade true %s" % jndi_name)

def undeploy_mail_resource(jndi_name):
    """
    undeploy the mail resource
    """
    mail_resources = run("/opt/glassfish/bin/asadmin list-javamail-resources")

    if mail_resources.__contains__(jndi_name):
        run("/opt/glassfish/bin/asadmin delete-javamail-resource %s" % jndi_name)

def deploy_java():
    render_settings_template()
    
    require("sudo_user")
    require("app_config_dir", "deploy_config_dir")
    rsync_as_user("%s/" % env.app_config_dir, "%s/" % env.deploy_config_dir, env.sudo_user, delete = True)
    require("war_file", "war_path")
    rsync_as_user(env.war_path, env.war_file, env.sudo_user)
    
    require("project_name")
#    sudo("/usr/local/sbin/deploy_glassfish_webapp.py %s %s" % (env.project_name, env.jdbc_cp_jndi_name), shell = False)
    remote_war_file=os.path.join(PATH_YELL_WEBAPPS, "%s.war" % env.project_name)

    undeploy(env.project_name)

    try:
       env.jdbc_cp_jndi_name
    except NameError:
       env.jdbc_cp_jndi_name = None
    except AttributeError:
       env.jdbc_cp_jndi_name = None

    if env.mail_resource_jndi_name is None:
        print "No JDBC resource to undeploy"
    else:
        undeploy_jdbc_connection_pool_resource(env.jdbc_cp_jndi_name)

    try:
       env.mail_resource_jndi_name
    except NameError:
       env.mail_resource_jndi_name = None
    except AttributeError:
       env.mail_resource_jndi_name = None

    if env.mail_resource_jndi_name is None:
        print "No mail resource to undeploy"
    else:
        undeploy_mail_resource(env.mail_resource_jndi_name)

    try:
       env.resources_to_deploy
    except NameError:
       env.resource_to_deploy = None
    except AttributeError:
       env.resources_to_deploy = None

    if env.resources_to_deploy is None:
        print "No resources to deploy"
    else:
        resource_file=os.path.join(PATH_YELL_CONF, env.config_dir_name, "glassfish-resources.xml")
        deploy_resources(resource_file)

    deploy(env.project_name, remote_war_file)
#    glassfish_service("stop-domain")
#    glassfish_service("start-domain")
