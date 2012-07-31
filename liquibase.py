import glob
import os.path
import sys
import tempfile

from fabric.api import local, env, sudo, runs_once, require, run
from fabric.contrib.project import rsync_project
from fabric.context_managers import cd

from operations import rsync_from_local
from utils import template_context, template_to_file

def run_script():
    render_settings_template()
    require("sudo_user")
    require("jdbc_url", "jdbc_username", "jdbc_password", "changelog_filename")

    remote_dir = sudo('mktemp -d', user = env.sudo_user)
    rsync_from_local(remote_dir)

    with cd('%s/processed-liquibase/changelog' % (remote_dir)):
        sudo("sh /usr/bin/liquibase" +
            " --driver=com.mysql.jdbc.Driver" +
            " --classpath=/usr/share/java/mysql-connector-java.jar" +
            " --url=%s" % (env.jdbc_url) +
            " --username=%s" % (env.jdbc_username) +
            " --password=%s" % (env.jdbc_password) +
            " --changeLogFile=%s" % (env.changelog_filename) +
            " update", user = env.sudo_user)

    sudo('rm -rf %s' % (remote_dir), user = env.sudo_user)

def setup_paths():
    require("java_root", "java_conf", "java_log", "project_name")

    env.db_script_archive = "%s-liquibase.tar.gz" % env.project_name

@runs_once
def render_settings_template():
    tempdir = tempfile.mkdtemp()
    env.project_path = tempdir
    local("tar -C'%s' -xzf '%s'" % (tempdir, env.db_script_archive))

    liquibase_source_dir = os.path.join(tempdir, 'liquibase')
    liquibase_target_dir = os.path.join(tempdir, 'processed-liquibase')

    os.mkdir(liquibase_target_dir)
    context = template_context(env.settings_vars)

    for (root, dirs, files) in os.walk(liquibase_source_dir):
        dirs[:] = [os.path.join(root, d) for d in dirs]
        files = [os.path.join(root, f) for f in files]

        for source_file in files:
            target_file = source_file.replace(liquibase_source_dir, liquibase_target_dir)
            if not (os.path.exists(os.path.dirname(target_file))):
                os.makedirs(os.path.dirname(target_file))
            template_to_file(source_file, target_file, context)

    env.deploy_db_script_dir = liquibase_target_dir
    env.tempdir = tempdir

