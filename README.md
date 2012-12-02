
![My image](http://i1.minus.com/jyaT1d3kWY1hH_e.jpg)
**Detect merge conflicts in realtime!** http://baboon-project.org
![My image](http://i3.minus.com/jbuMtAj0zbpNb1_e.jpg)

## What is Baboon ?

Do you waste your time in resolving merge conflicts with your favorite source
code manager? Do you want to get rid of "Merge Hell"?

Baboon is **the** solution for you! It's a lightweight daemon that detects
merge conflicts before they actually happen. In fact, it detects them in
**real time**.

## Wanna see Baboon running ?

```
$ baboon start
[synapse-agent 13:37:33] startup initialization...
[synapse-agent 13:37:36] ready 
[synapse-agent 13:39:19] No conflict detected with seyz and raphdg.
[synapse-agent 13:40:13] Conflict detected with seyz and raphdg.
> error: patch failed: synapse/config.py:23
> error: patch failed: synapse/resources/resources.py:89
[synapse-agent 13:44:54] No conflict detected with seyz and raphdg.
```

## How does it work ?
As soon as Baboon is installed and configured on your project's contributors
computers (a matter of seconds, honest! A minute, tops), it starts its job.

Baboon syncs your files in **real time** (well, every time you save one) with
the ones of your co-workers on a central server and simulates a merge of the
files.

If a conflict is detected, every contributor receives an alert to warn them that
eventually, a conflict will occur (Baboon even tells you on which file it will
happen).

Time to blame the culprit ! (Yeah, Baboon also tells you who originated the
conflict.)

He's lucky anyway. At this point, the merge conflict is super easy to solve,
it's small. Remember, you're warned in **real time**.

A few keywords:
* Python
* XMPP (with XEP-0060 and XEP-0065)
* Rsync (over XMPP)
* Git

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
