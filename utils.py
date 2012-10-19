"""
Generic utility classes for Fabric.

These should act as standalone functions and not modify Fabric's "env"
directly.
"""

import context_managers

import os
import shutil
import tempfile

from string import replace, Template
from xml.dom import minidom

from fabric.api import env, prompt, runs_once, sudo, local, puts, lcd
from fabric.context_managers import hide, cd, prefix
#from fabric.contrib.files import append


def django_manage_run(virtualenv, path, command, user, interactive=False):
    """
    Run a Django management command from a Python virtual environment.

        - virtualenv: Absolute path of Python virtualenv.
        - path: Absolute path of Django project.
        - command: Management command to run.
        - user: User to sudo as.
        - interactive: Whether to honour interactive prompts.
    """

    manage_py = os.path.join(path, "manage.py")
    cmd = "python %s %s" % (manage_py, command)

    if not interactive:
        cmd = "%s --noinput" % cmd

    with context_managers.virtualenv(virtualenv):
        sudo(cmd, user=user)


def play_run(path, command, user):
    """
    Run the command of a Play application.
    Always uses the environment `--%console`.
    """

    cmd = "%s %s %s --%%console" % (env.python_bin, env.play_bin, command)
    with cd(path):
        # Make absolutely sure resulting directories are readable by the
        # the Play process which runs as a different user.
        with prefix('umask 0002'):
            sudo(cmd, user=user)


@runs_once
def scm_get_ref(scm_type, use_default=False):
    if scm_type.lower() == "svn":
        if not use_default:
            puts("SCM reference must be a path " \
                "relative to the project's root URL.")
        default = "trunk"
    elif scm_type.lower() == "git":
        if not use_default:
            puts("SCM reference must be a named " \
                "'branch', 'tag' or 'revision'.")
        default = "master"

    if use_default:
        ref = default
    else:
        ref = prompt("SCM ref", default=default)

    return ref


@runs_once
def scm_get_info(scm_type, scm_ref=None, directory=False):

    scm_info = None

    if not scm_ref:
        scm_ref = scm_get_ref(scm_type, True)

    if not directory:
        directory = '.'

    if scm_type.lower() == "svn":
        with lcd(directory):
            with hide("running"):
                xml = local(
                    "svn info --xml",
                    capture=True,
                )
                dom = minidom.parseString(xml)
                scm_info = {
                    "type": scm_type,
                    "rev": dom.getElementsByTagName("entry")[0] \
                        .getAttribute("revision"),
                    "url": dom.getElementsByTagName("url")[0] \
                        .firstChild.wholeText,
                     "branch": scm_ref,
                }

    elif scm_type.lower() == "git":
        with lcd(directory):
            with hide("running"):
                revision = local(
                    "git describe --always",
                    capture=True,
                )
                repo = local(
                    "git remote -v | grep fetch",
                    capture=True,
                )
                scm_info = {
                    "type": scm_type,
                    "rev": revision,
                    "url": repo,
                    "branch": scm_ref,
                }

    return scm_info

@runs_once
def fetch_source(scm_type, scm_url, scm_ref=None, dirty=False):
    if dirty:
        tempdir = os.path.abspath(os.getcwd())
    else:
        tempdir = tempfile.mkdtemp()
        os.chmod(tempdir, 0755)

        if not scm_ref:
            scm_ref = scm_get_ref(scm_type)

        if scm_type.lower() == "svn":
            local(
                "svn checkout --quiet --config-option " \
                    "config:miscellany:use-commit-times=yes %s/%s %s"
                    % (
                        env.scm_url,
                        scm_ref,
                        tempdir,
                    ),
            )
        elif scm_type.lower() == "git":
            local("git clone --depth 1 %s %s" % (env.scm_url, tempdir))
            if scm_ref != "master":
                with lcd(tempdir):
                    try:
                        # Remote tag
                        local("git checkout -b %s %s" % (scm_ref, scm_ref))
                    except:
                        # Remote branch
                        local("git checkout -b %s origin/%s" % (scm_ref, scm_ref))

    #
    # Write out the version info
    #
    with lcd(tempdir):
        scm_info = scm_get_info(scm_type, scm_ref, tempdir)

        filename = "version"
        local("echo \"%s\" > %s" \
            % (
                replace(
                    str(scm_info),
                    ' (fetch)',
                    '',
                ),
                filename,
            )
        )

    if "scm_path" in env:
        tempdir = os.path.join(tempdir, env.scm_path)
    return tempdir


def delete_source_conditional(tempdir, dirty=False):
    if dirty:
        return

    if env.host != env.hosts[-1]:
        return

    shutil.rmtree(tempdir)


def render_settings_template(source, target, settings, debug):
    """
    Render a settings file from a template in a local checkout.
    """

    context = template_context(settings)

    # Treat as a string even though it's going to be rendered as unquoted.
    # Clobbers anything from env in the project's own fabfile because the
    # default should always be False.
    if "%s" % debug in ["True", "False"]:
        context["DEBUG"] = debug
    else:
        abort("local_settings.DEBUG may only be True or False")

    template_to_file(source, target, context)


def render_custom_templates(tempdir, settings, debug):
    """
    env.custom_config_files can be optionally used to specify key-value pairs
    of config templates to be processed. The structure looks like:

    env.custom_config_files = [
        { "source": "conf/foo.conf.template", "dest": "conf/foo.conf" },
        { "source": "conf/bar.conf.template", "dest": "conf/bar.conf" }
    ]
    """

    # Additional config templates are optional.
    if "custom_config_files" in env:
        for custom_config_file in env.custom_config_files:
            try:
                config_source = os.path.join(tempdir, custom_config_file['source'])
                config_target = os.path.join(tempdir, custom_config_file['dest'])
                render_settings_template(config_source, config_target, settings, debug)
            except KeyError:
                # Blow up if the structure isn't as expected.
                import sys, traceback
                traceback.print_exc()
                abort("The structure of env.custom_config_files is invalid")


@runs_once
def template_context(var_names):
    """
    Compiles a list of variables and their values from Fabric's env into a
    dictionary which can be used to render a template. Any values that aren't
    present in env are prompted for.
    """

    context = {}
    for var_name in var_names:
        var = env.get(var_name, None)

        if var == None:
            var = prompt('Enter settings var for %r:' % var_name)

        context[var_name] = var

    return context


def template_to_file(source, target, context):
    """
    Populate templated local_settings and place it in the tempdir to be
    rsynced. If `env.template_key = '$'` then it will use string.Template.
    Otherwise it will fallback to Python `%()s` string interpolation.
    """

    # make sure directory exists
    dir = os.path.dirname(target)
    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(target, "w") as target_file:
        with open(source) as source_file:
            if env.get('template_key') == '$':
                text = Template(source_file.read()).substitute(context)
            else:
                text = source_file.read() % context
        target_file.write(text)
