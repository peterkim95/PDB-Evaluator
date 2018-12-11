.PHONY: dev test clean
dev:
	virtualenv -p python3 venv && \
	source venv/bin/activate && \
	pip install -r requirements.txt
test:
	python -m pytest test/
clean:
	rm -rf venv

