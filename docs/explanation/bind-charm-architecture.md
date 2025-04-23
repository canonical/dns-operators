# Bind charm architecture

The following diagram shows the different modules of this charm
and how they interact with each other.

```
C4Component
title Bind Operator Components

UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")

Container_Boundary(bind-operator, "Bind Operator") {
    Component(events, "events.py", "Module", "Defines custom events")
    Component(exceptions, "exceptions.py", "Module", "Defines custom exceptions")
    Component(empty1, "")
    Component(charm, "charm.py", "Module", "Handles charm events and interactions with Juju")
    Component(empty2, "")
    Component(dns_data, "dns_data.py", "Module", "Manages DNS record data and conversions")
    Component(empty3, "")
    Component(empty4, "")
    Component(empty5, "")
    Component(models, "models.py", "Module", "Defines data models using Pydantic")
    Component(empty7, "")
    Component(bind, "bind.py", "Module", "Controls BIND workload execution")
    Component(empty6, "")
    Component(constants, "constants.py", "Module", "Defines constant values")
    Component(templates, "templates.py", "Module", "Provides templates for BIND configuration files")

    UpdateElementStyle(empty1,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty2,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty3,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty4,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty5,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty6,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty7,  $bgColor="#0000", $borderColor="#0000")

    Rel(charm, bind, "")
    Rel(bind, constants, "")
    Rel(bind, dns_data, "")
    Rel(bind, exceptions, "")
    Rel(bind, models, "")
    Rel(bind, templates, "")
    Rel(charm, constants, "")
    Rel(charm, dns_data, "")
    Rel(charm, exceptions, "")
    Rel(charm, models, "")
    Rel(dns_data, models, "")
    Rel(models, constants, "")
    Rel(charm, events, "")
}

UpdateElementStyle(bind, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(charm, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(dns_data, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(models, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(templates, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(constants, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(events, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(exceptions, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
```

## Scaling behavior

When Bind is scaled, only one unit gets the `active` status, all the others are in `standby`. A new `active` unit is elected whenever the previous one goes down.  
The `active` unit is the one updating the zone configuration of its workload and has Bind working as a primary authoritative server over them.  
All the `standby` units have Bind working as a secondary server, replicating the records via the usual DNS zone transfer.

## Charm code overview

The `src/charm.py` is the default entry point for a charm and has the `BindCharm` Python class which inherits from `CharmBase`. `CharmBase` is the base class from which all charms are formed, defined by [Ops](https://juju.is/docs/sdk/ops) Python framework for developing charms.

> See more in the Juju docs: [Charm](https://documentation.ubuntu.com/juju/latest/user/reference/charm/)

## Workload

The workload of this charm is a snap whose source code is in this repository, in the `charmed-bind` directory. The workload is operated through the `src/bind.py` module (which is able to start, stop, restart it, change its configuration files, set it up).  
The workload doesn't communicate with the charm. It merely executes the charm's orders.  
Outside of the snap, the chamr also sets up a systemd timer to be awaken every minute through the `ReloadBindEvent`. The hook responding to it makes sure that the configuration of Bind is up to date with the charm's relations.
