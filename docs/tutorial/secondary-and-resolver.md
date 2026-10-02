---
myst:
  html_meta:
    "description lang=en": "Follow the advanced DNS charms tutorial involving a secondary DNS server and resolver."
---
(tutorial_secondary_and_resolver)=

# Deploy a secondary DNS server and resolver

## Introduction

In the {ref}`first tutorial <tutorial_simple_deployment>`, we deployed a bind charm and served our first DNS record for `flying-saucer.local`. That setup works well for testing, but in production you would not expose the primary DNS server directly to clients. Instead, you would place a secondary DNS server in front of it and let a resolver handle the actual client queries.

In this tutorial we will extend our deployment with two new charms:

- [**dns-secondary**](https://charmhub.io/dns-secondary) -- a secondary DNS server that receives zone data from bind via zone transfers.
- [**dns-resolver**](https://charmhub.io/dns-resolver) -- a caching resolver that knows how to reach the secondary for our zone.

By the end, you will have a proper hidden primary architecture: bind holds the zone data, dns-secondary serves it to the outside world, and dns-resolver answers client queries. It will take us about 15 minutes.

### What you'll need

- A working Juju environment with a LXD cloud, as set up in the {ref}`first tutorial <tutorial_simple_deployment>`.

### What you'll do

1. Deploy bind and dns-integrator (recap from the first tutorial).
2. Deploy dns-secondary and integrate it with bind.
3. Deploy dns-resolver and integrate it with dns-secondary.
4. Verify the full resolution chain.

```{important}
Should you get stuck or notice issues, please get in touch on [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com) or [Discourse](https://discourse.charmhub.io/).
```

## Set things up

Follow the steps in {ref}`Your first DNS charm deployment <tutorial_simple_deployment>` up to and including the **Deploy dns-integrator** section. Once bind and dns-integrator are deployed, integrated, and active, come back here to continue.  
You don't need to scale up bind for the rest of this tutorial. If you've scaled up bind to three units and want to have exactly the same status as we're going to show here, remove those units with the `juju remove-unit` command.

At this point, `juju status` should look similar to:

```{terminal}
:user: ubuntu
:host: dns-dev

juju status

App             Version  Status  Scale  Charm           Channel      Rev  Exposed  Message
bind                     active      1  bind            latest/edge   81  no       active
dns-integrator           active      1  dns-integrator  latest/edge    2  no

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.79.131.37    53/tcp 53/udp  active
dns-integrator/0*  active    idle   1        10.79.131.165
```

## Deploy dns-secondary

The dns-secondary charm runs a secondary DNS server. It receives zone data from bind through zone transfers, so it always has an up-to-date copy of your records. Let's deploy it:

```bash
juju deploy dns-secondary --channel=latest/edge
```

After waiting a bit for the machine to come up, `juju status` should show:

```{terminal}
:user: ubuntu
:host: dns-dev

juju status

App             Version  Status   Scale  Charm           Channel      Rev  Exposed  Message
bind                     active       1  bind            latest/edge   81  no       active
dns-integrator           active       1  dns-integrator  latest/edge    2  no
dns-secondary            blocked      1  dns-secondary   latest/edge    3  no       Needs to be related with a primary charm

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.79.131.37    53/tcp 53/udp  active
dns-integrator/0*  active    idle   1        10.79.131.165
dns-secondary/0*   blocked   idle   4        10.79.131.21    53/tcp 53/udp  Needs to be related with a primary charm
```

The dns-secondary charm is in a `blocked` state because it doesn't know where to get its zone data from yet. Let's integrate it with bind:

```bash
juju integrate dns-secondary bind
```

After a moment, everything should be active:

```{terminal}
:user: ubuntu
:host: dns-dev

juju status

App             Version  Status  Scale  Charm           Channel      Rev  Exposed  Message
bind                     active      1  bind            latest/edge   81  no       active
dns-integrator           active      1  dns-integrator  latest/edge    2  no
dns-secondary            active      1  dns-secondary   latest/edge    3  no       1 zones, 1 primary addresses

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.79.131.37    53/tcp 53/udp  active
dns-integrator/0*  active    idle   1        10.79.131.165
dns-secondary/0*   active    idle   4        10.79.131.21    53/tcp 53/udp  1 zones, 1 primary addresses
```

The message "1 zones, 1 primary addresses" tells us that dns-secondary has received the `flying-saucer.local` zone from bind. Let's verify by querying the secondary directly for our TXT record:

```{terminal}
:user: ubuntu
:host: dns-dev

dig @<IP> message.flying-saucer.local TXT +short

"Hello"
```

```{note}
Replace `<IP>` with the public address of your dns-secondary unit, as shown in `juju status`. In my case, it would be `10.79.131.21`.
```

The secondary is serving the same record as the primary. Now let's look at the NS records for the zone:

```{terminal}
:user: ubuntu
:host: dns-dev

dig @<IP> flying-saucer.local NS +short

ns.flying-saucer.local.
```

Notice that the name server for the zone points to the secondary, not to bind. This is the hidden primary architecture in action: bind is the source of truth for the zone data, but it is not advertised as the name server. Only the secondary is publicly visible. This means you can manage and update your zone on bind without exposing it directly to client traffic.

## Deploy dns-resolver

With the secondary in place, we can now add a caching resolver. The dns-resolver charm runs a recursive resolver that learns about your zones through the authority chain. Let's deploy it:

```bash
juju deploy dns-resolver --channel=latest/edge
```

After the machine is ready, `juju status` should show:

```{terminal}
:user: ubuntu
:host: dns-dev

juju status

App             Version  Status   Scale  Charm           Channel      Rev  Exposed  Message
bind                     active       1  bind            latest/edge   81  no       active
dns-integrator           active       1  dns-integrator  latest/edge    2  no
dns-resolver             blocked      1  dns-resolver    latest/edge    1  no       Needs to be related with an authority charm
dns-secondary            active       1  dns-secondary   latest/edge    3  no       1 zones, 1 primary addresses

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.79.131.37    53/tcp 53/udp  active
dns-integrator/0*  active    idle   1        10.79.131.165
dns-resolver/0*    blocked   idle   5        10.79.131.150   53/tcp 53/udp  Needs to be related with an authority charm
dns-secondary/0*   active    idle   4        10.79.131.21    53/tcp 53/udp  1 zones, 1 primary addresses
```

The resolver is blocked because it needs to know which server is authoritative for our zone. We integrate it with dns-secondary:

```bash
juju integrate dns-secondary dns-resolver
```

After things settle, all charms should be active. Let's check with `juju status --relations` to see the full picture:

```{terminal}
:user: ubuntu
:host: dns-dev

juju status --relations

App             Version  Status  Scale  Charm           Channel      Rev  Exposed  Message
bind                     active      1  bind            latest/edge   81  no       active
dns-integrator           active      1  dns-integrator  latest/edge    2  no
dns-resolver             active      1  dns-resolver    latest/edge    1  no       1 zone, 1 authority address
dns-secondary            active      1  dns-secondary   latest/edge    3  no       1 zones, 1 primary addresses

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.79.131.37    53/tcp 53/udp  active
dns-integrator/0*  active    idle   1        10.79.131.165
dns-resolver/0*    active    idle   5        10.79.131.150   53/tcp 53/udp  1 zone, 1 authority address
dns-secondary/0*   active    idle   4        10.79.131.21    53/tcp 53/udp  1 zones, 1 primary addresses

Integration provider               Requirer                           Interface               Type     Message
bind:bind-peers                    bind:bind-peers                    bind-instance           peer
bind:dns-record                    dns-integrator:dns-record          dns_record              regular
bind:dns-transfer                  dns-secondary:dns-transfer         dns_transfer            regular
dns-resolver:dns-resolver-peers    dns-resolver:dns-resolver-peers    dns-resolver-instance   peer
dns-secondary:dns-authority        dns-resolver:dns-authority         dns_authority           regular
dns-secondary:dns-secondary-peers  dns-secondary:dns-secondary-peers  dns-secondary-instance  peer
```

The relations table shows the full chain: dns-integrator sends records to bind via `dns_record`, bind transfers zones to dns-secondary via `dns_transfer`, and dns-secondary provides authority information to dns-resolver via `dns_authority`.

Now let's verify that the resolver can answer queries for our zone:

```{terminal}
:user: ubuntu
:host: dns-dev

dig @<IP> message.flying-saucer.local TXT +short

"Hello"
```

```{note}
Replace `<IP>` with the public address of your dns-resolver unit, as shown in `juju status`. In my case, it would be `10.79.131.150`.
```

The resolver successfully resolved our TXT record. It did so by forwarding the query to dns-secondary, which holds the zone data it received from bind.

## Conclusion

You've reached the end of this tutorial. Building on the {ref}`first tutorial <tutorial_simple_deployment>`, you have now:

- deployed a secondary DNS server that receives zone data from bind
- deployed a caching resolver that answers client queries
- verified a full hidden primary architecture where bind is never directly exposed to clients

Your DNS deployment now follows a production-ready pattern: records are managed through dns-integrator, stored in bind, transferred to dns-secondary, and served to clients through dns-resolver.

### Tear things down

If you'd like to quickly tear things down, start by exiting the Multipass VM:

```bash
exit
```

And then you can proceed with its deletion:

```bash
multipass delete dns-dev
multipass purge
```
