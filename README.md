## About

A common set of [Fabric](http://fabfile.org) tasks to reduce duplication of code between projects. For simple projects, you should only need to import these tasks and define your site-specific variables. More complex projects can wrap these tasks and their own in a local `deploy()` method.

## Usage

1. Clone this `yellfabric` project.
1. Create a virtualenv with `python2.6`
1. Activate the virtualenv.
1. Install the requirements with `pip install -r requirements.txt`
1. Symlink `yellfabric` into your virtualenv's `site-packages`.
1. Create a `fabfile.py` within your project using the example `fabfile.py.example`

## Design

I was originally hoping to avoid global `env` variables and have each method accept and return it's own variables. However doing so would mean that they wouldn't be easily callable as standalone Fabric tasks, unless you specified all arguments by hand (like absolute paths) or wrap them in one-to-one classes, which kind of defeats the point of removing duplication. Instead I have attempted to make it clear what global variables each method uses and restrict utility methods for modifying them.
