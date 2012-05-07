### What is Baboon ?

Baboon is a tool to detect merge conflicts in realtime.

Baboon **never** changes your code. It's just a alerting system !

### How to install it ?

Baboon wants to run on all common platforms (Linux, OSX, Windows).

*For now, no install package is provided. The packages will be
available for the 0.1 version.*

### Development installation
You need a virtualenv to avoid polluting your system python installation.
I use the virtualenvwrapper tool.

### Virtualenvwrapper
    $ pip install virtualenvwrapper

For the documentation of virtualenvwrapper,
[take a look here](http://www.doughellmann.com/docs/virtualenvwrapper/index.html)
(including the installation process).

### Create the virtual environment
    $ mkvirtualenv baboon
    ...
### Enable the new virtual environment
    $ workon baboon

### Install all project dependencies
    $ pip install -r requirements.txt
    ...

