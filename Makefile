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
	pipenv run pytest --junitxml test-results/results.xml
	pipenv run coverage report
	pipenv run coverage html

install:
	poetry env remove 3.7
	poetry install --no-dev

install-dev:
	poetry env remove 3.7
	poetry install

reinstall-dev:
	poetry env remove 3.7
	make install-dev

update:
	poetry update

clean:
	rm -rf logfile*
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf test-results/
	find . -name "*.pyc" -exec rm -f {} \;

git-tag:
	git tag -a ${VERSION} -m "release ${VERSION}"`
	git push --tags

deploy-test:
	poetry run fab deploy-test ${BRANCH}

deploy:
	poetry run fab deploy ${VERSION}

migrate:
	poetry run fab migrate

sentry:
	sentry-cli releases new -p deneb "${VERSION}"
	sentry-cli releases set-commits --auto "${VERSION}"
	sentry-cli releases deploys "${VERSION}" new -e production

full-deploy: git-tag deploy migrate sentry

init-circle-venv:
	sudo pip install --upgrade pip
	sudo pip install --upgrade poetry
	make install-dev

docker:
	docker build -t deneb .
