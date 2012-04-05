# Yell Fabric

## About

A common set of [Fabric](http://fabfile.org) tasks to reduce duplication of code between projects. For simple projects, you should only need to import these tasks and define your site-specific variables. More complex projects can wrap these tasks and their own in a local `deploy()` method.

## Usage

1. Clone this `yellfabric` project.

        git clone git@github.com:YellLabs/yellfabric.git

1. Create a new virtualenv. Preferably with `python2.6`

        virtualenv -p python2.6 ~/venvs/fabric

1. Activate the virtualenv.

        source ~/venvs/fabric/bin/activate

1. Install the project requirements.

        pip install -r yellfabric/requirements.txt

1. Symlink `yellfabric` into your virtualenv's `site-packages`

        ln -s ~/projects/yellfabric ~/venvs/fabric/lib/python2.6/site-packages/

1. Configure your SSH details in `~/.fabricrc`
 - If using Fabric <1.4 set a username and private key path.

            user = USERNAME
            key_file = ~/.ssh/id_rsa

 - If using Fabric >= 1.4 you can use your existing ssh_config.

            use_ssh_config = true

## Switches

- `env.custom_config_files`: A list of dictionaries detailing additional config templates to be rendered and copied.

        env.custom_config_files = [
            { "source": "conf/foo.conf.template", "dest": "conf/foo.conf" },
            { "source": "conf/bar.conf.template", "dest": "conf/bar.conf" }
        ]

## Design

I was originally hoping to avoid global `env` variables and have each method accept and return it's own variables. However doing so would mean that they wouldn't be easily callable as standalone Fabric tasks, unless you specified all arguments by hand (like absolute paths) or wrap them in one-to-one classes, which kind of defeats the point of removing duplication. Instead I have attempted to make it clear what global variables each method uses and restrict utility methods for modifying them.

## TODO

1. Add some form of version checking between this common project and the individual projects that utilise it, to enforce feature compatibility.
1. Use `env` globals less. If at all possible. I dislike this assumed magic.
1. Move individual project variables like hostnames out to `.ini` files. We shouldn't have to re-tag the project when we add more frontend nodes.
1. Tidy up tempdir after Java deployments.
1. Abort if rsync skips any source files.
1. Possibly the same for increasing log verbosity in Java deployments.
1. Check presence of WSGI file before touching. Will catch naming issues.
1. Change pip(1) log location.
