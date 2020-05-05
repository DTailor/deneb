import os

from dotenv import load_dotenv
from fabric import Connection, task

load_dotenv(verbose=True)

SSH_USER = os.environ["SSH_USER"]
SSH_HOST = os.environ["SSH_HOST"]

POETRY = f"/home/{SSH_USER}/.local/bin/poetry"
PY = "3.7.0"


@task
def compose_test(c, branch):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb-test/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git fetch --tags")
        captain.run(f"git checkout {branch}")
        captain.run(f"git pull origin {branch}")
        captain.run("make compose")


@task
def deploy(c, version):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git fetch --tags")
        captain.run(f"git checkout {version}")
        captain.run(f"git pull origin {version}")
        captain.run("make compose")


@task
def deploy_test(c, branch):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb-test/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git fetch --tags")
        captain.run(f"git checkout {branch}")
        captain.run(f"git pull origin {branch}")
        captain.run(f"{POETRY} env use {PY}")
        captain.run(f"{POETRY} install")
        captain.run(f"{POETRY} run python -m pytest")


@task
def deploy(c, version):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("git reset --hard HEAD")
        captain.run("git fetch -ap")
        captain.run("git fetch --tags")
        captain.run(f"git checkout {version}")
        captain.run(f"git pull origin {version}")
        captain.run(f"{POETRY} env use {PY}")
        captain.run(f"{POETRY} install")
        captain.run(f"{POETRY} run python -m pytest")


@task
def migrate(c):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("python -m poetry run alembic upgrade head")


@task
def full_run(c):
    captain = Connection(f"{SSH_USER}@{SSH_HOST}")
    with captain.cd("/apps/deneb/"):
        captain.run("python -m poetry run python -m deneb full-run")
