#!/usr/bin/env python

from setuptools import setup, find_packages

requires = []
with open('requirements.txt', 'r') as f:
    requires = f.readlines()

setup(name='baboon',
      version='0.1',
      description='Detect merge conflict in realtime.',
      author='Sandro Munda, Raphael De Giusti',
      author_email='munda.sandro@gmail.com',
      url='http://baboon-project.org',
      download_url='https://github.com/SeyZ/baboon/tarball/master',
      packages=find_packages(),
      install_requires=[requires],
      scripts=['bin/baboon', 'bin/baboond'],
      data_files=[('conf', ['conf/baboondrc', 'conf/baboonrc'])],

      # Take the latest develop version of SleekXMPP
      dependency_links=['https://github.com/fritzy/SleekXMPP/tarball/develop#egg=sleekxmpp-1.1.5beta']
     )
