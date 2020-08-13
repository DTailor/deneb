-include .env

.PHONY : help

PY_VERSION = 3.8.5

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
	poetry env use ${PY_VERSION}
	poetry install --no-dev

install-dev:
	pip install --user --pre poetry -U
	poetry env use ${PY_VERSION}
	poetry install

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
	docker build -t ${DOCKER_REPO} .

push:
	docker push ${DOCKER_REPO}:latest

compose:
	docker pull dtailor/deneb:latest --quiet
	docker-compose down
	docker-compose up --force-recreate -d
	docker-compose logs -f
