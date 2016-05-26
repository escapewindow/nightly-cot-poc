#!/bin/sh
gpg2 --no-default-keyring --secret-keyring gpg/sec.gpg --keyring gpg/pub.gpg "$@"
