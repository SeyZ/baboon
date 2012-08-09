## What is Baboon ?

Do you waste your time in resolving merge conflicts with your favorite source
code manager ? Do you want to get rid of "Merge Hells" ?

Baboon is **the** solution for you ! It's a lightweight daemon that detects
merge conflicts before they actually happen. In fact, it detects them in
**real time**

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
* Git
* Rsync over XMPP
* Socks5 proxy (XEP-0065)
* Pubsub (XEP-0060)

## Quickstart

### It's your project

```
pip install baboon
baboon register <username>
baboon create <project_name>
baboon start
```

### You're a contributor

```
pip install baboon
baboon register <username>
baboon join <project_name>
baboon start
```

## Contribution

The source code is available on Github (no seriously ?) ! **Any** contributions
are welcome. Fork the project !

