![My image](http://i1.minus.com/jyaT1d3kWY1hH_e.jpg)
**Detect merge conflicts in realtime!**
[http://baboon-project.org](http://baboon-project.org)
![My image](http://i3.minus.com/jbuMtAj0zbpNb1_e.jpg)

## What is Baboon?

One single merge conflict is pretty easy to solve. However, you might take
several days before realizing there is one conflict. The longer you wait, the
more conflicts you will have to solve.

**Overlooking them will lead you to a merge hell.**

Baboon is a lightweight daemon that detects merge conflicts in realtime.

## Installation

```pip install baboon``` or ```easy_install baboon```

## Quickstart

### New baboon project:

```
baboon register <nick>
baboon create <project> <project-path>
baboon start
```

### Join an existing baboon project:

```
baboon register <nick>
baboon join <project> <project-path>
baboon init <project> <git-project-url>
baboon start
```

## Documentation
Check out the [Wiki pages!](https://github.com/SeyZ/baboon/wiki).

If you encounter a bug, post it to the issue tracker.  For questions, feedback
or whatever, feel free to contact me at
[sandro@munda.me](mailto:sandro@munda.me)

## How does it work ?

Baboon syncs your files in **real time** (well, every time you save one) with
the ones of your contributors on a centralized server and simulates a merge of
the files.

If a conflict is detected, everyone notified. Time to blame the culprit! He is
lucky anyway. At this point, the merge conflict is super easy to solve: it is
small. Remember, you are warned in **real time**.

A few keywords:
* Python
* XMPP (with XEP-0060 and XEP-0065)
* Rsync (over XMPP)
* Git

## License

(the MIT license)

Copyright (C) 2012 Sandro Munda <sandro@munda.me>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/SeyZ/baboon/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

