#!/usr/bin/env python3

from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

setup(
    name='apistar_pydantic',
    version='0.0.1',
    description="pydantic support for APIStar",
    long_description=readme,
    author="Pedro Sousa Lacerda",
    author_email='pslacerda@gmail.com',
    url='github.com/pslacerda/apistar_pydantic',
    py_modules=['apistar_pydantic'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'apistar',
        'pydantic',
        'coreapi',
        'coreschema',
        'uritemplate'
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
        'Framework :: APIStar',
    ],
    test_suite='tests',
    tests_require=[
        'pytest'
    ],
)
