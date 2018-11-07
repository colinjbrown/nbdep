from setuptools import setup, find_packages


try:
    long_desc = open('README.md').read()
except:
    long_desc = ''

setup(
    name="nbdepv",
    url="https://github.com/colinjbrown/nbdepv",
    author="Colin Brown",
    author_email="cbrown12@umassd.edu",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "argparse==1.1",
        "msgpack==0.5.6"
    ],
    include_package_data=True,
    description="A package for outputting libraries imported in a notebook",
    long_description=long_desc,
)