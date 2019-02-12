import os

from fabric import Connection, task

SSH_USER = os.environ["SSH_USER"]
SSH_HOST = os.environ["SSH_HOST"]


@task
def deploy(c):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git checkout develop")
        captain.run("git pull")
        captain.run("pipenv sync")
        captain.run("pipenv clean")


@task
def full_run(c):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("pipenv run python -m deneb full-run")
