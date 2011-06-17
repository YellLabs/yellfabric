from fabric.api import run, sudo

def virtualenv_run(path, command):
    with prefix('source %/bin/activate' % path):
        run("python %s" % command)

def django_manage_run(command):
    virtualenv_run("./manage.py %s" % command, env.release_path)

def pip_requirements():
    virtualenv_run("pip install --requirement %s")

def render_local_settings(source, target, context):
    """
    Populate templated local_settings and place it in the tempdir to be rsynced.
    """

    with open(target, "w") as target_file:
        with open(source) as source_file:
            text = source_file.read() % context
        target_file.write(text)
