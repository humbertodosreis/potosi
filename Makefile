enable:
	source `poetry env info --path`/bin/activate

disable:
	deactivate

install: enable
	poetry install
