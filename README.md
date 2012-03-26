### What is Baboon ?

After installing Baboon, each developer has a baboon on top of the
shoulder. After each file save, Baboon shouts to other baboons the
changes of the file. The other Baboons try to apply the changes to
their sides and reply if a conflict is detected.

Baboon **never** changes your code. He just shouts !

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

