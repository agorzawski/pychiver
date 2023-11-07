install:
	pip install --editable . --user --index-url https://artifactory.esss.lu.se/artifactory/api/pypi/pypi-virtual/simple

uninstall:
	pip uninstall esslogbook

# Always install as developer for now
#install:
#	pip install . --user
