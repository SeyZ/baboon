## What is Baboon ?

Do you waste your time in resolving merge conflicts with your favorite source
code manager ? Do you want to get rid of "Merge Hells" ?

Baboon is **the** solution for you ! It's a lightweight daemon that detects
merge conflicts before they actually happen. In fact, it detects them in
**real time**.

## How does it work ?
As soon as Baboon is installed and configured (a matter of seconds, honest,
a minute top) on your project's contributors computers, it starts its job.

Baboon syncs in **real time** your files (well, everytime you save one) with
the ones of your co-workers on a central server and simulates a merge of the
files.

If a conflict is detected, every contributor receives an alert to warn them that
eventually, a conflict will occur (Baboon even tells you on which file it will
happen).

Time to blame the culprit ! (Yeah, Baboon also tells you who originated the
conflict)

He's lucky anyway. At this point, the merge conflict is super easy to solve,
it's small. Remember, you're warned in **real time**.

A few keywords:
* Python
* XMPP (with XEP-0060 and XEP-0065)
* Rsync (over XMPP)
* Git

## Quickstart

### It's your project

```
pip install baboon
baboon register <nick>
baboon create <project> <path>
baboon init <project> <git-url>
baboon start
```

### You're a contributor

```
pip install baboon
baboon register <nick>
baboon join <project> <path>
baboon init <project> <git-url>
baboon start
```

## Contribution

The source code is available on Github (no seriously ?) ! **Any** contributions
are welcome. Fork the project !

## License

(the MIT license)

Copyright (C) 2012 Sandro Munda <munda.sandro@gmail.com>

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
