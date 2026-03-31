# Your first DNS charm deployment

Imagine that you just acquired the lovely domain `flying-saucer.local` and that you want to host your own authoritative DNS server.
In a traditional setup, you would need to learn how to install and configure a DNS server like BIND on Ubuntu and then get through the hassle of understanding how to create a high availability setup. But with our DNS charm, this is going to be easy and you'll be able to do it in no time.

In this short tutorial we will deploy an authoritative DNS charm locally on your machine and create a test zone for you to query. It will take us about 20 minutes.  
If you're new to the charming world, don't worry: we'll explain every step.

### What you'll need

- A local system, e.g., a laptop, with AMD64 or ARM64 architecture
  which has sufficient resources to launch a virtual machine with 4
  CPUs, 4 GB RAM, and a 50 GB disk.
- Familiarity with Linux.

The RAM and disk space are necessary to set up all the required software and
to facilitate the creation of the rock and charm. If your local system has less
than the sufficient resources, the tutorial will take longer to complete.

### What you'll do

1. Deploy the bind charm.
2. Deploy the dns-integrator charm and relate it to bind.
3. Edit your zone and query it.
4. Scale up your charm to make it highly available.

```{important}
Should you get stuck or notice issues, please get in touch on [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com) or [Discourse](https://discourse.charmhub.io/).
```

## Set things up

We recommend starting from a clean Ubuntu installation. If you don't have one available, you can create one using [Multipass](https://multipass.run/docs/install-multipass).

`````{tab-set}

````{tab-item} Ubuntu

Is Multipass already installed and active? Check by running:

```bash
snap services multipass
```

If you see the `multipass` service but it isn't "active", run:

```bash
sudo snap start multipass
```

If you get an error saying `snap "multipass" not found`, install it with:

```bash
sudo snap install multipass
```

````

````{tab-item} Windows

See the [Multipass installation instructions](https://multipass.run/docs/install-multipass) and switch to **Windows** in the dropdown menu.

````

````{tab-item} macOS

See the [Multipass installation instructions](https://multipass.run/docs/install-multipass) and switch to **macOS** in the dropdown menu.

````

`````

Once Multipass is ready, create the VM with the following command:

```bash
multipass launch --cpus 4 --memory 4G --disk 50G --name dns-dev 24.04
```

Finally, once the VM is up, open a shell into it:

```bash
multipass shell dns-dev
```

```{note}
Unless stated otherwise, we will work entirely within the VM from now on.
```

Use [Concierge](https://github.com/canonical/concierge) to set up Juju:

```bash
sudo snap install --classic concierge
sudo concierge prepare -p machine
```

This installs Concierge and uses it to install and configure Juju with a local LXD cloud.

For this tutorial, Juju must be bootstrapped to a LXD controller. Concierge should
complete this step for you. You can verify by running:

```bash
juju controllers
```

You should see output similar to:

```{terminal}
:output-only:
Controller      Model    User   Access     Cloud/Region         Models  Nodes    HA  Version
concierge-lxd*  testing  admin  superuser  localhost/localhost       2      1  none  3.6.20
```

Delete the default `testing` model that Juju creates. We will create a new model for this tutorial in the next step.

```bash
juju destroy-model testing
```

## Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from
your usual work, create a new model using the following command.

```bash
juju add-model dns-tutorial
```

## Deploy bind

Now that we have everything we need, let's deploy our DNS server!

```bash
juju deploy bind --channel=latest/edge
```

Running `juju status` should show you the following after waiting a bit for things to settle:

```{terminal}
App   Version  Status  Scale  Charm  Channel      Rev  Exposed  Message
bind           active      1  bind   latest/edge   80  no       active

Unit     Workload  Agent  Machine  Public address  Ports          Message
bind/0*  active    idle   0        10.124.97.210   53/tcp 53/udp  active
```

Our bind DNS server is now deployed and running. You can see it's listening on ports 53/tcp and 53/udp, which are the standard DNS ports.
We can check the health of our DNS server using the built-in status record:

```{terminal}
dig @10.124.97.210 status.service.test TXT +short

"ok"
```

```{note}
Replace `10.124.97.210` with the public address of your bind unit, as shown in `juju status`.
```

## Deploy dns-integrator

We now have a fully functioning DNS server but we still need a way to specify the records that we want to serve.
That's what the dns-integrator charm is for. Let's deploy it:

```bash
juju deploy dns-integrator --channel=latest/edge
```

After waiting a bit, `juju status` should show:

```{terminal}
App             Version  Status   Scale  Charm           Channel      Rev  Exposed  Message
bind                     active       1  bind            latest/edge   80  no       active
dns-integrator           blocked      1  dns-integrator  latest/edge    2  no       Waiting for some configuration

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.124.97.210   53/tcp 53/udp  active
dns-integrator/0*  blocked   idle   1        10.124.97.236                  Waiting for some configuration
```

The dns-integrator charm is waiting for some configuration.
Let's create a DNS record for our `flying-saucer.local` domain. We'll add a simple TXT record:

```bash
juju config dns-integrator requests="message flying-saucer.local 600 IN TXT Hello"
```

Let's check the status again:

```{terminal}
App             Version  Status   Scale  Charm           Channel      Rev  Exposed  Message
bind                     active       1  bind            latest/edge   80  no       active
dns-integrator           blocked      1  dns-integrator  latest/edge    2  no       Waiting for integration

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.124.97.210   53/tcp 53/udp  active
dns-integrator/0*  blocked   idle   1        10.124.97.236                  Waiting for integration
```

The dns-integrator is still in a `blocked` state because it needs to be related to a DNS server.

```bash
juju integrate bind dns-integrator
```

And now, everything should be active:

```{terminal}
App             Version  Status  Scale  Charm           Channel      Rev  Exposed  Message
bind                     active      1  bind            latest/edge   80  no       active
dns-integrator           active      1  dns-integrator  latest/edge    2  no

Unit               Workload  Agent      Machine  Public address  Ports          Message
bind/0*            active    executing  0        10.124.97.210   53/tcp 53/udp  active
dns-integrator/0*  active    executing  1        10.124.97.236
```

Now let's query the TXT record we just created for our `flying-saucer.local` domain:

```{terminal}
:user: ubuntu
:host: dns-dev

dig @10.124.97.210 message.flying-saucer.local TXT +short

"Hello"
```

```{note}
Replace `10.124.97.210` with the public address of your bind unit, as shown in `juju status`.
```

Our DNS server is up and serving records. You've just deployed a fully functional authoritative DNS server using Juju charms!

## Scale up

Bind can be scaled up to prevent outages and divide incoming requests among multiple units.
To do that, you just need to run: 

```
juju add-unit -n 2 bind
```

After letting things settle down a bit, we can now see:

```{terminal}
:user: ubuntu
:host: dns-dev

juju status

App             Version  Status  Scale  Charm           Channel      Rev  Exposed  Message
bind                     active      3  bind            latest/edge   80  no       active
dns-integrator           active      1  dns-integrator  latest/edge    2  no

Unit               Workload  Agent  Machine  Public address  Ports          Message
bind/0*            active    idle   0        10.124.97.210   53/tcp 53/udp  active
bind/1             active    idle   2        10.124.97.65    53/tcp 53/udp
bind/2             active    idle   3        10.124.97.201   53/tcp 53/udp
dns-integrator/0*  active    idle   1        10.124.97.236
```

Now bind has three units! We can query each one with `dig` to get the same results.
Note that only one unit is marked as "active" at a time. This unit will act as a hidden primary and you should not expose it publicly, leaving the task of responding to client queries to the other units instead.

## Conclusion

You've reached the end of this tutorial. You have now:
- deployed a functioning DNS server
- instructed it to serve a list of records
- scaled it up using a hidden primary architecture

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
