(changelog)=

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each revision is versioned by the date of the revision.

## 2026-09-27

- feat: Add rules to the DNS policy application, managed from its admin website, that automatically approve or deny the pending record requests of a domain and its subdomains. No rule exists by default. The ACME challenge rule approves the `_acme-challenge` TXT records of a domain that the same requirer has an approved A or AAAA record for, or that is automatically allocated to it. A reviewer can override the automatic decisions.
- feat: Let the `_acme-challenge` TXT requests under the `ddns-domain` of the DNS policy charm through to the policy application.
- feat: Send the identifier of the DNS policy charm installation along with the record requests, so that the policy application tells apart the requirers of different installations sharing the same relation id.

## 2026-08-30

- feat: Add the `ddns-domain` configuration to the DNS policy charm. When set, every requirer of the `dns-record-provider` endpoint is allocated a unique domain under that suffix, published back through the `dns_record` relation and resolved upstream by an A/AAAA record and a wildcard record. Requests for the configured suffix or its subdomains are rejected.
- feat: Add the `dns-policy-peers` peer relation to the DNS policy charm, which holds the identifier the automatically allocated domains are scoped to.
- fix: Only create the `dns_record` namespace secret from the leader unit, as an application owned secret can't be managed by a non-leader unit.

## 2026-08-26

- feat: Add the optional `ddns-domain` (provider) and `ddns-addresses` (requirer) fields to the `dns_record` relation, so a provider can hand an automatically allocated domain to each of its requirers.

## 2026-06-18

- docs: Migrate the RTD documentation URL under the Canonical domain.

## 2026-05-31

- chore: move dns_record lib from dns-record to dns-integrator charm namespace.

## 2026-04-08

- docs: Add upgrade documentation.

## 2026-03-03

- docs: Set up Read the Docs project for publishing the documentation.

## 2025-12-17

- Moved `bind-charm-architecture.md` from Explanation to Reference category.
