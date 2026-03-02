(reference_components)=

# Components

The DNS operators consist of the following DNS charms:

1. `bind`: A machine charm managing a bind instance configured as a primary DNS server. See the [bind README](https://github.com/canonical/dns-operators/blob/main/bind-operator/README.md) for more information.
2. `dns-policy`: A subordinate charm that adds a policy layer in front of the bind charm. See the [dns-policy README](https://github.com/canonical/dns-operators/blob/main/dns-policy-operator/README.md) for more information.
3. `dns-integrator`: An integrator charm that allows the creation of record request through its configuration. See the [dns-integrator README](https://github.com/canonical/dns-operators/blob/main/dns-integrator-operator/README.md) for more information.
4. `dns-resolver`: A resolver charm that provides a single point of configuration for all the requirers using the same DNS server. See the [dns-resolver README](https://github.com/canonical/dns-operators/blob/main/dns-resolver-operator/README.md) for more information.
5. `dns-secondary`: A secondary charm that provides a hidden primary setup by serving the zones without leaking any IP address of the primary deployment. See the [dns-secondary README](https://github.com/canonical/dns-operators/blob/main/dns-secondary-operator/README.md) for more information.

The project also contains the snapped workload of some charms:

1. `charmed-bind`: A snapped bind specifically made for the `bind` charm. See the [charmed-bind README](https://github.com/canonical/dns-operators/blob/main/charmed-bind/README.md) for more information.
2. `charmed-dns-policy`: A snapped Django application specifically made for the `dns-policy` charm. See the [charmed-dns-policy README](https://github.com/canonical/dns-operators/blob/main/charmed-dns-policy/README.md) for more information.