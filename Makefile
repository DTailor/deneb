.PHONY : help

help:
	@echo "test - run tests"
	@echo "install - pipenv install either reinstall if present"
	@echo "install-dev - pipenv install with dev packages either reinstall if present."
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
	pipenv --rm
	pipenv install

install-dev:
	pipenv --rm
	pipenv install --dev

update:
	pipenv update

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
	pipenv run fab deploy-test ${BRANCH}

deploy:
	pipenv run fab deploy ${VERSION}

migrate:
	pipenv run fab migrate

sentry:
	sentry-cli releases new -p deneb "${VERSION}"
	sentry-cli releases set-commits --auto "${VERSION}"
	sentry-cli releases deploys "${VERSION}" new -e production

full-deploy: git-tag deploy migrate sentry

init-circle-venv:
	sudo pip install --upgrade pip
	sudo pip install --upgrade pipenv
	make install-dev

docker:
	docker build -t deneb .
