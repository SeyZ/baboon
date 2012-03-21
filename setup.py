#!/usr/bin/env python

from setuptools import setup, find_packages

requires = ['sleekxmpp >= 1.0',
            'dnspython >= 1.9.4',
            'pyinotify >= 0.9.3',
            'GitPython >= 0.3.0',
            'hgapi >= 1.1.0',
            ]

setup(name='baboon',
      version='0.1',
      description='Realtime conflicts detector',
      author='Sandro Munda, Raphael De Giusti',
      author_email='munda.sandro@gmail.com',
      url='http://baboon-project.org',
      packages=find_packages(),
      install_requires=[requires]
      )
