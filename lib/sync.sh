#!/bin/sh

set -e

LIB_DIR="$(cd "$( dirname "$0" )" && pwd)"
REPO_ROOT="$(cd "$LIB_DIR/.." && pwd)"

for project in \
  "bind-operator" \
  "dns-integrator-operator" \
  "dns-policy-operator"
do
  mkdir -p "$REPO_ROOT/$project/lib/charms"
  cp -r "$LIB_DIR/charms/bind" "$REPO_ROOT/$project/lib/charms/"
done

for project in \
  "bind-operator" \
  "dns-resolver-operator"
do
  mkdir -p "$REPO_ROOT/$project/lib/charms"
  cp -r "$LIB_DIR/charms/dns_authority" "$REPO_ROOT/$project/lib/charms/"
done
