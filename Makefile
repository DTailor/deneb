-include .env

.PHONY : help

POETRY_VERSION = 1.1.8
PY_VERSION = 3.9

help:
	@echo "test - run tests"
	@echo "install - poetry install either reinstall if present"
	@echo "install-dev - poetry install with dev packages either reinstall if present."
	@echo "update - update pip packages."
	@echo "init-venv - init and install py environment."
	@echo "clean - remove all temporary files (safe)."
	@echo "deploy - deploy code on production."
	@echo "git-tag - make git tag and push changes to git."
	@echo "deploy-test - deploy the test built from specified branch."
	@echo "migrate - run sql migrations."
	@echo "sentry - create a sentry releases and push changes."
	@echo "full-deploy - git tag +  deploy + migrate + sentry"
	@echo "docker - build docker image."

test:
	poetry run pytest --junitxml test-results/results.xml
	poetry run coverage report
	poetry run coverage html

install:
	pip3 install --user --pre poetry==${POETRY_VERSION} -U
	python3 -m poetry env use ${PY_VERSION}
	python3 -m poetry install --no-dev

install-dev:
	pip3 install --user --pre poetry==${POETRY_VERSION} -U
	python3 -m poetry env use ${PY_VERSION}
	python3 -m poetry install

reinstall-dev:
	poetry env remove ${PY_VERSION} || true
	make install-dev

update:
	poetry update

clean:
	rm -rf logfile*
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf test-results/
	rm -rf htmlcov/
	rm -rf *.egg-info
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf dist/
	rm -rf .cache


git-tag:
	git tag -a ${VERSION} -m "release ${VERSION}"
	git push --tags

deploy-test:
	poetry run fab compose-test ${BRANCH}

deploy: docker push
	poetry run fab compose ${VERSION}

migrate:
	poetry run fab migrate

sentry:
	sentry-cli --url https://sentry.io/ releases --org ${SENTRY_ORG} new -p deneb "${VERSION}"
	sentry-cli --url https://sentry.io/ releases --org ${SENTRY_ORG} set-commits --auto "${VERSION}"
	sentry-cli --url https://sentry.io/ releases --org ${SENTRY_ORG} deploys "${VERSION}" new -e production
	sentry-cli --url https://sentry.io/ releases --org ${SENTRY_ORG} finalize "${VERSION}"

full-deploy: migrate git-tag sentry deploy

init-circle-venv:
	sudo pip install --upgrade pip
	sudo pip install --upgrade poetry
	make install-dev

docker:
	docker build --tag ${DOCKER_REPO} .

push:
	docker push ${DOCKER_REPO}:{VERSION}

compose:
	docker pull dtailor/deneb:{VERSION}
	docker-compose down
	docker-compose up --force-recreate -d
	docker-compose logs -f
