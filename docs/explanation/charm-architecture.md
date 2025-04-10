# Charm architecture

DNS operators are a family of charms used to integrate a fully functional DNS solution in Juju.
The core charm is the bind-operator, which acts as a primary DNS server.
The underlying workload uses BIND, packaged as a snap with other tooling to help administer it from the charm perspective.

The following diagram shows how these charms are intended to be used with other charms:

```mermaid
C4Context
title DNS charms story

Container_Boundary(is-model, "IS model") {
  
  Component(bind, "Bind charm")
  Component(dns-policy, "DNS policy")

  Rel(dns-policy, bind, "dns_record")
  UpdateRelStyle(dns-policy, bind, $textColor="green", $lineColor="green", $offsetX="-20", $offsetY="10")

  Component(httpreq, "HTTP Request Lego Provider")
  Component(lego, "Lego")
  Component(tls-policy, "TLS policy")

  Rel(httpreq, bind, "dns_record")
  Rel(lego, httpreq, "API")
  Rel(tls-policy, lego, "tls-certificates")
  UpdateRelStyle(httpreq, bind, $textColor="green", $lineColor="green", $offsetX="10")
  UpdateRelStyle(lego, httpreq, $textColor="purple", $lineColor="purple", $offsetY="10")
  UpdateRelStyle(tls-policy, lego, $textColor="red", $lineColor="red")
}

Container_Boundary(app-model, "App model") {
    Component(app-1, "Application 1")
    Component(ingress, "Ingress")
    Component(app-2, "Application 2")

    Rel(app-1, ingress, "ingress")
    Rel(app-2, ingress, "ingress")
    UpdateRelStyle(app-1, ingress, $textColor="blue", $lineColor="blue", $offsetX="10")
    UpdateRelStyle(app-2, ingress, $textColor="blue", $lineColor="blue", $offsetX="10")
}

Rel(ingress, dns-policy, "dns_record")
Rel(ingress, tls-policy, "tls-certificates")
UpdateRelStyle(ingress, dns-policy, $textColor="green", $lineColor="green")
UpdateRelStyle(ingress, tls-policy, $textColor="red", $lineColor="red")

Person(operator, "Operator")
Rel(operator, dns-policy, "approve/denies requests")
UpdateRelStyle(ingress, dns-policy, $textColor="grey", $lineColor="grey", $offsetX="50")

Rel(operator, tls-policy, "approve/denies requests")
UpdateRelStyle(ingress, tls-policy, $textColor="grey", $lineColor="grey", $offsetY="20")

UpdateRelStyle(operator, dns-policy, $offsetY="-40", $offsetX="-60")
UpdateRelStyle(operator, tls-policy, $offsetY="-200", $offsetX="-155")
```

The bind-operator is usually deployed with dns-policy to enable human and/or automated approval of incoming DNS record requests.
The workload of dns-policy is a Django application packaged as a snap with additional tooling. Since both the workloads of bind-operator and dns-policy
are snaps, they can work on the same machine. It was therefore decided to make dns-policy a subordinate charm.

The following diagram shows the interactions between bind-operator, dns-policy, and external components of a typical deployment of the DNS charms:

```mermaid
C4Container
title DNS charms components

UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")

Rel(operator, charmed-dns-policy, "API", "approve/denies requests")

Component(postgresql, "Postgresql")
Person(operator, "Operator")

Component(empty1, "")
Component(empty2, "")
Component(empty3, "")
UpdateElementStyle(empty1,  $bgColor="#0000", $borderColor="#0000")
UpdateElementStyle(empty2,  $bgColor="#0000", $borderColor="#0000")
UpdateElementStyle(empty3,  $bgColor="#0000", $borderColor="#0000")

Component(dns-integrator, "DNS integrator")
Rel(dns-integrator, dns-policy, "dns_record")
UpdateRelStyle(dns-integrator, dns-policy, $textColor="green", $lineColor="green")


Rel(charmed-dns-policy, postgresql, "database")
UpdateRelStyle(charmed-dns-policy, postgresql, $textColor="blue", $lineColor="blue")

Container_Boundary(machine-1, "Machine 1") { 

  Component(charmed-dns-policy, "DNS policy snap")

  Component(empty6, "")
  UpdateElementStyle(empty6,  $bgColor="#0000", $borderColor="#0000")

  Component(charmed-bind, "Bind snap")

  Component(empty0, "")
  UpdateElementStyle(empty0,  $bgColor="#0000", $borderColor="#0000")

  Component(empty5, "")
  UpdateElementStyle(empty5,  $bgColor="#0000", $borderColor="#0000")

  Component(empty7, "")
  UpdateElementStyle(empty7,  $bgColor="#0000", $borderColor="#0000")

  Component(dns-policy, "DNS policy charm")

  Component(empty8, "")
  UpdateElementStyle(empty8,  $bgColor="#0000", $borderColor="#0000")

  Component(bind, "Bind charm")

  Rel(dns-policy, bind, "dns_record")
  UpdateRelStyle(dns-policy, bind, $textColor="green", $lineColor="green")

  Rel(bind, charmed-bind, "API", "Update DNS records")
  Rel(dns-policy, charmed-dns-policy, "API", "Update DNS requests")
}
```
