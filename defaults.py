from fabric.api import env

# Default Python interpreter when creating virtual environments.
env.python_bin = 'python2.6'

# Root path of Apache's vhosts.
env.root = '/srv/www/httpd'

# Disable bash login simulation. It generates errors when used with sudo
# because the sudo'ed user doesn't have access to the original user's
# home directory and profile files.
env.shell = '/bin/bash -c'

# Default to none.
env.sudo_user = None
env.http_proxy = None
env.https_proxy = None
