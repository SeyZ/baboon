## Development installation
You need a virtualenv to avoid polluting your system python installation.
I use the virtualenvwrapper tool.

## Virtualenvwrapper
    $ pip install virtualenvwrapper

For the documentation of virtualenvwrapper,
[take a look here](http://www.doughellmann.com/docs/virtualenvwrapper/index.html)
(including the installation process).

## Create the virtual environment
    $ mkvirtualenv baboon
    New python executable in baboon/bin/python
    Installing setuptools............done.
    Installing pip...............done.
    virtualenvwrapper.user_scripts creating ~/workspace/virtenvs/baboon/bin/predeactivate
    virtualenvwrapper.user_scripts creating ~/workspace/virtenvs/baboon/bin/postdeactivate
    virtualenvwrapper.user_scripts creating ~/workspace/virtenvs/baboon/bin/preactivate
    virtualenvwrapper.user_scripts creating ~/workspace/virtenvs/baboon/bin/postactivate
    virtualenvwrapper.user_scripts creating ~/workspace/virtenvs/baboon/bin/get_env_details

## Enable the new virtual environment
    $ workon baboon


