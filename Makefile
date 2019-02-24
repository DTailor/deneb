test:
	pipenv run pytest --junitxml test-results/results.xml

install:
	pipenv install

install-dev:
	pipenv install --dev

upgrade:
	pipenv update

init-env:
	sudo pip install pipenv
	sudo pip install pipenv pip --upgrade
	pipenv install --dev

clean:
	rm -rf logfile*
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf test-results/
	find . -name "*.pyc" -exec rm -f {} \;

deploy:
	pipenv run fab deploy
