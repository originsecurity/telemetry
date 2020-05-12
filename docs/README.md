# Documentation

## Before you start

### Terminology

* We call it our Security Telemetry pipeline, because it's a **pipeline** (unidirectional event flow) that security **telemetry** (metrics and logs) flows through.
* Logstash also has a feature called [pipelines](https://www.elastic.co/guide/en/logstash/current/pipeline-to-pipeline.html). We use these in our docker image for pipeline to pipeline communication, so that our logstash config files are easier to manage.
* Your CI/CD system will also have pipelines too.

Be aware that the word `pipeline` is used in a few different contexts here.

### Assumptions

**These stacks rely on some assumptions**, they assume that:

1. You already have a VPC and preferred subnets that you want to deploy Logstash to.
1. Destination S3 bucket/s already exist for Logstash to archive to.
1. If you want to use AWS Cloud Map for DNS-based service discovery, that the Route 53 zone, and Cloud Map namespace already exist.
1. If you need to inject secrets into your Logstash environment variables that these secrets are stored in Secrets Manager, and
    * if you are using a _Customer Managed_ CMK to encrypt those secrets, that all secrets are encrypted with the same key.

## Next steps

For the best results, review the documentation in this order:

1. [Service Types](service_types.md)
1. [Configuration File Format](configuration.md)
1. [Getting Started Guide](getting_started.md)
1. [Logstash How-to and Tips](logstash.md)
