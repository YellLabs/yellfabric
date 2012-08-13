import os.path
import tempfile
import shutil

from fabric.api import local, env, runs_once, require, run
from fabric.contrib.project import rsync_project
from fabric.context_managers import cd

@runs_once
def migratedb():
    setup_paths()

    require("jdbc_url", "jdbc_username", "jdbc_password", "changelog_filename")

    local_tempdir = tempfile.mkdtemp()
    local("tar -C'%s' -xzf '%s'" %
        (local_tempdir, env.db_script_archive))

    remote_tempdir = run('mktemp -d')
    rsync_project(
        local_dir="%s/" % local_tempdir,
        remote_dir="%s/" % remote_tempdir,
        delete=True)

    with cd(os.path.join(remote_tempdir, 'liquibase', 'changelog')):
        run("sh /usr/bin/liquibase" +
            " --driver=com.mysql.jdbc.Driver" +
            " --classpath=/usr/share/java/mysql-connector-java.jar" +
            " --url=%s" % (env.jdbc_url) +
            " --username=%s" % (env.jdbc_username) +
            " --password=%s" % (env.jdbc_password) +
            " --changeLogFile=%s" % (env.changelog_filename) +
            " update")

    run('rm -rf %s' % (remote_tempdir))
    shutil.rmtree(local_tempdir)

@runs_once
def setup_paths():
    require("project_name")

    env.db_script_archive = "%s-liquibase.tar.gz" % env.project_name
