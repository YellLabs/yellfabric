import glob
import os.path
import shutil
import sys
import tempfile

from fabric.api import local, env, sudo, lcd, run, runs_once
from fabric.contrib.project import rsync_project

from utils import template_to_file
from fabric.operations import prompt

@runs_once
def _prepare():
    """
    Prepare the files to upload
    """
    env.log_dir = "/var/log/tomcat6/%s" % env.artifact_id
    env.war_file_name = '%s.war' % env.artifact_id
    env.war_file = '/usr/share/java/wars/%s' % env.war_file_name
    env.app_config_dir = '/etc/yell/%s' % env.artifact_id
    
    workdir = tempfile.mkdtemp()
    local("tar -C'%s' -xzf '%s'" % (workdir, env.deploy_config_archive))
    src_config_dir = os.path.join(workdir, 'config')
    dest_config_dir = os.path.join(workdir, 'processed-config')
    os.mkdir(dest_config_dir)
    for src in os.listdir(src_config_dir):
        template_to_file(os.path.join(src_config_dir, src),
                         os.path.join(dest_config_dir, src),
                         env)
    env.deploy_config_dir = dest_config_dir

def rsync_as_user(remote_dir, local_dir, user, delete = False, exclude = ()):
    extra_opts = '--rsync-path="sudo -u %s rsync"' % user
    rsync_project(remote_dir, local_dir, exclude = exclude, delete = delete, extra_opts = extra_opts)

def deploy_java():
    _prepare()
    
    rsync_as_user("%s/" % env.app_config_dir, "%s/" % env.deploy_config_dir, "labs.deploy", delete = True)
    rsync_as_user(env.war_file, env.deploy_war_file, "labs.deploy")
    
    sudo("/usr/local/sbin/deploy_tomcat_webapp.py %s" % env.artifact_id, shell = False)
