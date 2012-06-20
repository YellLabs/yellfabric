import os
import operations

from fabric.api import env, runs_once, require

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

    operations.fetch_render_copy(ref, False, dirty, True)
