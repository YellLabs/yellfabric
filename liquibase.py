import glob
import os.path
import sys
import tempfile
import shutil

from fabric.api import local, env, sudo, runs_once, require, run
from fabric.contrib.project import rsync_project
from fabric.context_managers import cd

from operations import rsync_from_local

def run_script():
    require("sudo_user")
    require("jdbc_url", "jdbc_username", "jdbc_password", "changelog_filename")

    local_tempdir = tempfile.mkdtemp()
    local("tar -C'%s' -xzf '%s'" %
        (local_tempdir, env.db_script_archive))
    env.tempdir = local_tempdir

    remote_tempdir = sudo('mktemp -d', user = env.sudo_user)
    rsync_from_local(remote_tempdir)

    with cd(os.path.join(remote_tempdir, 'liquibase', 'changelog')):
        sudo("sh /usr/bin/liquibase" +
            " --driver=com.mysql.jdbc.Driver" +
            " --classpath=/usr/share/java/mysql-connector-java.jar" +
            " --url=%s" % (env.jdbc_url) +
            " --username=%s" % (env.jdbc_username) +
            " --password=%s" % (env.jdbc_password) +
            " --changeLogFile=%s" % (env.changelog_filename) +
            " update", user = env.sudo_user)

    sudo('rm -rf %s' % (remote_tempdir), user = env.sudo_user)
    shutil.rmtree(local_tempdir)

def setup_paths():
    require("java_root", "java_conf", "java_log", "project_name")

    env.db_script_archive = "%s-liquibase.tar.gz" % env.project_name
