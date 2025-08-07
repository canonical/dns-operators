#!/bin/sh

set -e

LIB_DIR="$(cd "$( dirname "$0" )" && pwd)"
REPO_ROOT="$(cd "$LIB_DIR/.." && pwd)"

for project in \
  "bind-operator" \
  "dns-policy-operator"
do
  mkdir -p "$REPO_ROOT/$project/lib/charms"
  cp -fr "$LIB_DIR/charms/bind" "$REPO_ROOT/$project/lib/charms/"
done

# shellcheck disable=SC2043
for project in \
  "dns-integrator-operator"
do
  mkdir -p "$REPO_ROOT/$project/lib/charms"
  cp -fr "$LIB_DIR/charms/dns_record" "$REPO_ROOT/$project/lib/charms/"
done

for project in \
  "bind-operator" \
  "dns-resolver-operator"
do
  mkdir -p "$REPO_ROOT/$project/lib/charms"
  cp -r "$LIB_DIR/charms/dns_authority" "$REPO_ROOT/$project/lib/charms/"
done
