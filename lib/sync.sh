#!/bin/sh

LIB_DIR="$(cd "$( dirname "$0" )" && pwd)"
REPO_ROOT="$(cd "$LIB_DIR/.." && pwd)"

for project in \
  "bind-operator" \
  "dns-integrator-operator" \
  "dns-policy-operator"
do
  cp -r "$LIB_DIR/charms/bind" "$REPO_ROOT/$project/lib/charms/"
done
