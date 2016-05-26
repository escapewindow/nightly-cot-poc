#!/bin/sh
gpg --no-default-keyring --secret-keyring ./sec.gpg --keyring ./pub.gpg "$@"
