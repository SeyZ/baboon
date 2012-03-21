#!/usr/bin/env python

from setuptools import setup, find_packages

requires = []
with open('requirements.txt', 'r') as f:
    requires = f.readlines()

setup(name='baboon',
      version='0.1',
      description='Realtime conflicts detector',
      author='Sandro Munda, Raphael De Giusti',
      author_email='munda.sandro@gmail.com',
      url='http://baboon-project.org',
      packages=find_packages(),
      install_requires=[requires]
      )
