# Bind Snap

This snap is meant to be the workload of the [bind-operator](https://github.com/canonical/dns-operators/bind-operator) charm.  

## Get started

### Install the Snap
The snap can be installed directly from the Snap Store.  
[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/charmed-bind)


### Build the Snap
The steps outlined below are based on the assumption that you are building the snap with the latest LTS of Ubuntu.  If you are using another version of Ubuntu or another operating system, the process may be different.

#### Clone repository
```bash
git clone git@github.com:canonical/dns-operators.git
cd dns-operators/charmed-bind
```
#### Install and configure prerequisites
```bash
sudo snap install snapcraft
sudo snap install lxd
sudo lxd init --auto
```
#### Pack and install the Snap
```bash
snapcraft pack
sudo snap install ./charmed-bind_*.snap --devmode
```

## Learn more
* [Read more](https://charmhub.io/bind/docs)

## Project and community
* [Issues](https://github.com/canonical/dns-operators/issues)
* [Contributing](https://charmhub.io/bind/docs/how-to-contribute)
* [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
