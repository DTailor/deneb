import os

from fabric import Connection, task

SSH_USER = os.environ["SSH_USER"]
SSH_HOST = os.environ["SSH_HOST"]


@task
def deploy_test(c, branch):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb-test/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git fetch --tags")
        captain.run(f"git checkout {branch}")
        captain.run(f"git pull origin {branch}")
        captain.run("source ./.env && poetry install")


@task
def deploy(c, version):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git fetch --tags")
        captain.run(f"git checkout {version}")
        captain.run(f"git pull origin {version}")
        captain.run("source ./.env && poetry install")


@task
def migrate(c):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("source ./.env && poetry run alembic upgrade head")


@task
def full_run(c):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("source ./.env && poetry run python -m deneb full-run")
