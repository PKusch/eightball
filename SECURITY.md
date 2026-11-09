# Security

eightball runs a small web server on your own machine and sends your questions to a local model. Please report it if you can make any of these happen:

- **The server answers from outside your machine** when it was started with the defaults (it listens on 127.0.0.1, and other web pages may not call it unless `--cors` is given).
- **A request that crashes the server or makes it hang**, rather than getting a plain error back.
- **A health, safety, money or feelings question that gets a confident yes or no** instead of "please ask a person". The guard is a word list, so a question that slips past it is worth reporting even if it is not a security hole in the usual sense.
- **A file named on the command line being read or written somewhere it should not be.**

A wrong answer about an ordinary question is a normal issue, not a security report.

## How to report

Open a new issue titled **Security report**. Say only that you have found something, and leave out the details, so nothing is made public before it is fixed. I will reply and we can move the details somewhere private.

## What to expect

This is a one-person project, so there is no formal response time. A report that comes with steps to reproduce it gets read promptly.

## Supported versions

Only the latest commit on `main` is supported.
