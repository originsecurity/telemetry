# Service types

1. Service Types (HERE)
1. [Configuration File Format](configuration.md)
1. [Getting Started Guide](getting_started.md)
1. [Logstash How-to and Tips](logstash.md)


The telemetry pipeline supports configuring three different types of services, based on how each log source is received.

Some services, like Syslog require a load balancer.
Some services can be load balanced by the client or won't work via NLB, like Syslog over UDP.
Other services are pull-based and don't listen on any ports at all.

These different types of service require different components in AWS. Categorising each type of service is how the CDK app automatically builds the right components for each different type of service.

## `nlb` Services

NLB services are attached to a network load balancer.

**All services are attached to the same load balancer** and the listener port/s are configured the same as the container ports. Avoid port conflicts.

## `cloudmap` Services

AWS Cloud Map services are configured to register with a Cloud Map namespace for DNS-based service discovery. Use this for services where the client performs load balancing based on DNS discovery, or for UDP-based services which are not currently supported by NLB with Fargate.

Each service has its own DNS name in Cloud Map, port conflicts are okay.

## `pull` Services

Pull services do not listen for incoming traffic. They _pull_ events from another source.
Pull services are not attached to a load balancer and are not configured for Cloud Map service discovery.

Pull services are useful in the _inbound stack_ when using Logstash to pull events from another message queue first, like as Azure Event Hubs or RabbitMQ.

The queue `processor` service is also an example of a _pull-based_ service. While the `processor` service is part of the _outbound stack_, it still operates in a pull/push mechanism.
