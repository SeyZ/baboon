#!/usr/bin/env python

from os.path import join
from setuptools import setup, find_packages
from distutils.sysconfig import get_python_lib

requires = []
with open('requirements.txt', 'r') as f:
    requires = f.readlines()

long_description = """Do you waste your time in resolving merge conflicts with
your favorite source code manager ? Do you want to get rid of "Merge Hells" ?
Baboon is the solution for you ! It's a lightweight daemon that detects merge
conflicts before they actually happen. In fact, it detects them in real time.
"""

setup(
    name='baboon',
    version='0.1.0',
    description='Detect merge conflict in realtime.',
    long_description=long_description,
    author='Sandro Munda',
    author_email='munda.sandro@gmail.com',
    license='MIT',
    url='http://baboon-project.org',
    download_url='https://github.com/SeyZ/baboon/tarball/master',
    packages=find_packages(),
    install_requires=[requires],
    scripts=['bin/baboon', 'bin/baboond'],
    data_files=[('{0}/baboon/conf'.format(get_python_lib()), [
        'baboon/conf/baboondrc', 'baboon/conf/baboonrc'])],
    dependency_links=['https://github.com/fritzy/SleekXMPP/tarball/develop'
                      '#egg=sleekxmpp-1.1.5beta'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: BSD',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: Other',
        'Programming Language :: Cython',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Quality Assurance'
    ],
)
