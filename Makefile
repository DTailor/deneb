.PHONY : help
help :
	@echo "test - run tests"
	@echo "install - pipenv install"
	@echo "install-dev - pipenv install with dev packages."
	@echo "update - update pip packages."
	@echo "init-venv - init and install py environment."
	@echo "clean - remove all temporary files (safe)."
	@echo "deploy - deploy code on production."

test:
	pipenv run pytest --junitxml test-results/results.xml
	pipenv run coverage report
	pipenv run coverage html

install:
	pipenv install

install-dev:
	pipenv install --dev

update:
	pipenv update

clean:
	rm -rf logfile*
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf test-results/
	find . -name "*.pyc" -exec rm -f {} \;

deploy:
	pipenv run fab deploy ${VERSION}

migrate:
	pipenv run fab migrate

sentry:
	sentry-cli releases new -p deneb "${VERSION}"
	sentry-cli releases set-commits --auto "${VERSION}"
	sentry-cli releases deploys "${VERSION}" new -e production

init-circle-venv:
	sudo pip install --upgrade pipenv
	sudo pip install --upgrade pip
	make install-dev
