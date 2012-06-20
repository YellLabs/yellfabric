from fabric.api import env

# Default Python interpreter when creating virtual environments.
env.python_bin = "python2.6"

# Root directory for Python and Java deployments.
env.python_root = "/srv/www/httpd"
env.static_root = "/srv/www/httpd"
env.java_root = "/usr/share/java/wars"
env.jar_root = "/usr/share/java/jars"
env.java_conf = "/etc/yell"
env.java_log = "/var/log/tomcat6"
env.play_root = "/srv/play"
env.play_bin = "/opt/play/play"

# Disable bash login simulation. It generates errors when used with sudo
# because the sudo'ed user doesn't have access to the original user's
# home directory and profile files.
env.shell = "/bin/bash -c"

# Default to none.
env.sudo_user = None
env.http_proxy = None
env.https_proxy = None
