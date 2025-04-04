```mermaid
C4Context
title DNS charms story

Container_Boundary(is-model, "IS model") {
  
  Component(bind, "Bind charm")
  Component(dns-policy, "DNS policy")

  Rel(dns-policy, bind, "dns_record")
  UpdateRelStyle(dns-policy, bind, $textColor="green", $lineColor="green")

  Component(httpreq, "HTTP Request Lego Provider")
  Component(lego, "Lego")
  Component(tls-policy, "TLS policy")

  Rel(httpreq, bind, "dns_record")
  Rel(lego, httpreq, "API")
  Rel(tls-policy, lego, "tls-certificates")
  UpdateRelStyle(httpreq, bind, $textColor="green", $lineColor="green")
  UpdateRelStyle(lego, httpreq, $textColor="purple", $lineColor="purple")
  UpdateRelStyle(tls-policy, lego, $textColor="red", $lineColor="red")
}

Container_Boundary(app-model, "App model") {
    Component(ingress, "Ingress")
    Component(app-1, "Application 1")
    Component(app-2, "Application 2")

    Rel(app-1, ingress, "ingress")
    Rel(app-2, ingress, "ingress")
    UpdateRelStyle(app-1, ingress, $textColor="blue", $lineColor="blue")
    UpdateRelStyle(app-2, ingress, $textColor="blue", $lineColor="blue")
}

Rel(ingress, dns-policy, "dns_record")
Rel(ingress, tls-policy, "tls-certificates")
UpdateRelStyle(ingress, dns-policy, $textColor="green", $lineColor="green")
UpdateRelStyle(ingress, tls-policy, $textColor="red", $lineColor="red")

Person(operator-dns, "Operator")
Rel(operator-dns, dns-policy, "approve/denies requests")
UpdateRelStyle(ingress, dns-policy, $textColor="grey", $lineColor="grey")

Person(operator-tls, "Operator")
Rel(operator-tls, tls-policy, "approve/denies requests")
UpdateRelStyle(ingress, tls-policy, $textColor="grey", $lineColor="grey")
```
