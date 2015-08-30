#!/usr/bin/env python
import setuptools

import dockertest


setuptools.setup(
    name='dockertest',
    version=dockertest.__version__,
    url='https://github.com/dave-shawley/dockertest',
    description='Make dockerized services available to tests',
    long_description='\n'+open('README.rst').read(),
    py_modules=['dockertest'],
    install_requires=open('requirements.txt').readlines(),
    tests_require=open('test-requirements.txt').readlines(),

    zip_safe=True,
    platforms='any',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Development Status :: 3 - Alpha',
    ],
)
