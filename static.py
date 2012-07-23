import os
import utils
import operations

from fabric.api import env, runs_once, require, run, local

@runs_once
def setup_paths():

    require("static_root", "project_name", "vhost")

    env.vhost_path = os.path.join(env.static_root, env.vhost)
    env.project_path = os.path.join(env.vhost_path)
    env.config_source = "index.html.template"
    env.config_target = "index.html"

def deploy_static(ref=None, dirty=False):
    """
    Deploy static files to a vhost.
    """
    build_cmd = create_custom_command(env.require_path, env.build_config)
    operations.fetch_render_copy(ref, False, dirty, True, build_cmd)

def create_custom_command(require_path, build_conf_path):
    """
    Create a custom build command for require.js
    """
    def build_local_cmd(tempdir):
        abs_require_path = os.path.join(tempdir, require_path)
        abs_build_conf_path = os.path.join(tempdir, build_conf_path)
        local("node %s -o %s" % (abs_require_path, abs_build_conf_path))
    return build_local_cmd
