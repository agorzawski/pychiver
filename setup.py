import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="pychiver",
    version="0.7.3",
    author="Arek Gorzawski",
    author_email="arek.gorzawski@ess.eu",
    description="A python utility for EPICS archiver, SaveAndRestore and waveform handling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "requests",
        "python-dateutil",
        "pandas",
        "matplotlib",
        "numpy",
        "pyepics",
        "python-gitlab",
        "py-epicsarchiver>=0.5",
    ],
    packages=setuptools.find_packages(),
)
