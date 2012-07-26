### What is Baboon ?

Are you annoyed by resolving merge conflicts ? Do you want to forget what is a
"Merge Hell" ?

Baboon is **the** tool for you ! It's a lightweight daemon that detects merge
conflicts after each file save in a project.

### How it works ?
Each contributor has Baboon installed on his computer. Baboon must be
configured to watch a specific project path (see the documentation, it's done
in 10 seconds !).

Each Baboon is connected to a *XMPP* server. On each file save in your project
directory, your baboon wakes up and sync the changes through a Socks5 proxy
(XEP-0065) between you and a Baboon server.

When Baboon server detects the end of the sync, it runs a background merge
task. The result is sent (XEP-0060) to all contributors of your project to warn
if there's a merge conflict or not.

If there's a merge conflict, don't panic. The conflict is there from a very
short time (from your last file save action) !

### Contribution
**Any** contributions are welcome. Fork the project !

