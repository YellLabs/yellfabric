import glob
import os.path
import os
import tempfile
import shutil

from fabric.api import local, env, sudo, lcd, run
from fabric.contrib.project import rsync_project

from utils import template_to_file
from fabric.operations import prompt

def init_settings():
    env.log_dir = "/var/log/tomcat6/%s" % env.artifact_id
    env.war_file_name = '%s.war' % env.artifact_id
    env.war_file = '/usr/share/java/wars/%s' % env.war_file_name
    env.app_config_dir = '/etc/yell/%s' % env.artifact_id

def rsync_as_user(remote_dir, local_dir, user, delete = False, exclude = ()):
    extra_opts = '--rsync-path="sudo -u %s rsync"' % user
    rsync_project(remote_dir, local_dir, exclude = exclude, delete = delete, extra_opts = extra_opts)

def deploy():
    init_settings()
    prompt('Base URL of version to deploy:', 'base_url')

    war_url = '%s.war' % env.base_url
    config_archive_url = '%s-config.tar.gz' % env.base_url

    workdir = tempfile.mkdtemp()
    print("Workdir: %s" % workdir)
    with lcd(workdir):
        local("wget -O '%s' '%s'" % (env.war_file_name, war_url))
        local("wget -O- '%s' | tar xz" % config_archive_url)

        src_config_dir = os.path.join(workdir, "config")
        dest_config_dir = os.path.join(workdir, "processed_config")
        os.mkdir(dest_config_dir)
        for src in os.listdir(src_config_dir):
            template_to_file(os.path.join(src_config_dir, src),
                             os.path.join(dest_config_dir, src),
                             env)

        rsync_as_user("%s/" % env.app_config_dir, "%s/" % dest_config_dir, "labs.deploy")
        rsync_as_user(env.war_file, env.war_file_name, "labs.deploy", delete = True)

        sudo("/usr/local/sbin/deploy_tomcat_webapp.py %s" % env.artifact_id, shell = False)
    shutil.rmtree(workdir)
