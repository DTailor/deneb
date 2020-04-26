.PHONY : help

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
	source ./.env || true && poetry run pytest --junitxml test-results/results.xml
	poetry run coverage report
	poetry run coverage html

install:
	poetry env remove 3.7 || true
	poetry install --no-dev
	poetry env use 3.7

install-dev:
	poetry install

reinstall-dev:
	poetry env remove 3.7 || true
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
	poetry run fab deploy-test ${BRANCH}

deploy:
	poetry run fab deploy ${VERSION}

migrate:
	poetry run fab migrate

sentry:
	sentry-cli --url https://sentry.io/ releases new -p deneb "${VERSION}"
	sentry-cli --url https://sentry.io/ releases set-commits --auto "${VERSION}"
	sentry-cli --url https://sentry.io/ releases deploys "${VERSION}" new -e production
	sentry-cli --url https://sentry.io/ releases finalize "${VERSION}"

full-deploy: git-tag deploy migrate sentry

init-circle-venv:
	sudo pip install --upgrade pip
	sudo pip install --upgrade poetry
	poetry env remove 3.8 || true
	make install-dev
	poetry env use 3.8

docker:
	docker build -t deneb .
