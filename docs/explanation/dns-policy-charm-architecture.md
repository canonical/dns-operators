# DNS policy charm architecture

The following diagram shows the different modules of this charm
and how they interact with each other.

```
C4Component
title DNS policy charm Components

UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")

Container_Boundary(dns-policy-operator, "DNS policy charm") {

    Component(templates, "templates.py", "Module", "Provides templates")
    Component(timer, "timer.py", "Module", "Handles timer-based events")
    Component(database, "database.py", "Module", "Manages database interactions")
    Component(constants, "constants.py", "Module", "Defines constant values")
    Component(empty6, "")
    Component(charm, "charm.py", "Module", "Handles charm events and interactions with Juju")
    Component(dns_policy, "dns_policy.py", "Module", "Implements DNS policy logic")
    Component(empty4, "")
    Component(models, "models.py", "Module", "Defines data models using Pydantic")

    UpdateElementStyle(empty4,  $bgColor="#0000", $borderColor="#0000")
    UpdateElementStyle(empty6,  $bgColor="#0000", $borderColor="#0000")

    Rel(charm, constants, "")
    Rel(charm, database, "")
    Rel(charm, dns_policy, "")
    Rel(charm, models, "")
    Rel(charm, timer, "")
    Rel(database, constants, "")
    Rel(dns_policy, constants, "")
    Rel(models, constants, "")
    Rel(timer, constants, "")
    Rel(timer, templates, "")
}

UpdateElementStyle(charm, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(constants, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(database, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(dns_policy, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(models, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(templates, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
UpdateElementStyle(timer, $fontColor="black", $bgColor="lightblue", $borderColor="gray")
```
