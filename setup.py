#!/usr/bin/env python3

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

setup(
    name='apistar-pydantic',
    version='0.0.5',
    description="Better handler parameters for APIStar (and pydantic support)",
    long_description=readme,
    author="Pedro Sousa Lacerda",
    author_email='pslacerda@gmail.com',
    url='https://github.com/pslacerda/apistar_pydantic',
    py_modules=['apistar_pydantic'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'apistar',
    ],
    license="MIT license",
    keywords='apistar_pydantic',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=[
        'pytest',
        'pydantic',  # for pydantic models
        'aiofiles',  # for ASyncApp
    ],
)
