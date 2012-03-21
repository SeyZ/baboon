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

