# Origin Security - Telemetry Pipeline

## Before you start

**A note on terminology:**

* We call it our Security Telemetry pipeline, because it's a **pipeline** (unidirectional event flow) that security **telemetry** (metrics and logs) flows through.
* Logstash also has a feature called [pipelines](https://www.elastic.co/guide/en/logstash/current/pipeline-to-pipeline.html). We use these in our docker image for pipeline to pipeline communication, so that our logstash config files are easier to manage.
* Your CI/CD system will also have pipelines too.

Be aware that word pipeline is used if a few different contexts here.

**These stacks rely on some assumptions**, they assume that:

1. You already have a VPC and preferred subnets that you want to deploy Logstash to.
1. Destination S3 bucket/s already exist for logstash to archive to.
1. If you want to use AWS Cloud Map for DNS-based service discovery, that the Route 53 zone, and Cloud Map namespace already exist.
1. If you need to inject secrets into your Logstash environment variables that these secrets are stored in Secrets Manager, and
    * if you are using a _Customer Managed_ CMK to encrypt those secrets, that all secrets are encrypted with the same key.

## CloudFormation Stacks

This app consists of five CloudFormation stacks, and two docker images:

### 1. `{stage_name}-telemetry-logstash-in-ecr`

This stack only provides the ECR repository to contain the `logstash-in` docker image.

### 2. `{stage_name}-telemetry-logstash-in`

This stack contains the Fargate cluster, services, load balancer, and other components to support receiving inbound events to the telemetry pipeline.

### 3. `{stage_name}-telemetry-queue`

This stack contains the Kinesis data stream that acts as our queue/buffer, and a DynamoDB table that Logstash uses for Kinesis consumer coordination.

### 4. `{stage_name}-telemetry-logstash-out-ecr`

This stack only provides the ECR repository to contain the `logstash-out` docker image.

### 5. `{stage_name}-telemetry-logstash-out`

This stack contains the Fargate cluster, service and associated components to support pulling events from Kinesis and sending them outbound to analytics (Splunk), and archive (S3).

### Diagram

![Image of diagram showing pipeline components and corresponding stacks.](/docs/images/pipeline_diagram.png)

## Getting Started

Review the [documentation](/docs/README.md) for how to get started.

## License

This code to help you build the required AWS infrastructure, and Logstash sample configuration files, is licensed under the MIT license; Logstash itself is not.

Refer to [https://github.com/elastic/logstash/blob/master/LICENSE.txt](https://github.com/elastic/logstash/blob/master/LICENSE.txt) for details on Logstash's license.
