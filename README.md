# Origin Security - Telemetry Pipeline

Security organisations are continuously challenged to collect more logs, from more devices; a problem that is typically solved with a Security Information and Event Management (SIEM) platform.

Many traditional SIEMs try to solve all problems at once; at Origin, we decided to break the traditional model into discrete components, and use a combination of the best free and open source software and cloud services to run our SIEM smarter and cheaper, while avoiding vendor lock-in.

1. **Shipping and Parsing**:
    * We use a combination of Elastic Beats and Logstash, with some​ cloud-native pipelines where they make sense, for things like CloudTrail or VPC flow logs.
1. **Analytics**:
    * We split off only the subset of logs we need for our day-to-day operations and alerting into Splunk.
    * We use Amazon Athena to query our historical logs directly from archive, or any sources that aren't in Splunk.​
1. **Archive**:
    * We compress and partition our logs in Logstash before storing them in S3 for long term retention at very low cost.​

This repo consists of:

* An AWS CDK app that will help with provisioning Fargate and the associated AWS components to run Logstash without servers.
* Two docker images and associated Logstash configuration files to get you started.

## Architecture

1. We run a separate Logstash pipeline for each log source we’re ingesting, and we run them as separate microservices on Fargate.
1. We push the events from these listener services into a central Kinesis data stream – which acts as a buffer.
1. Then, we pull events from the data stream in batches and process them in a processor service, which is also Logstash running on Fargate.
    * This service parses any unstructured events, typically from syslog sources, it partitions events by time and event attributes, and it compresses these partitioned batches before uploading them to S3.
    * This service is also responsible for filtering off a subset of the event stream to a Splunk Universal Forwarder (**not included** in this stack).

![Image of diagram showing pipeline components and corresponding stacks.](/docs/images/pipeline_diagram.png)

## Cost

AWS pricing can vary significantly from region to region. You must review and understand the costs of the CloudFormation templates this stack outputs _before_ you deploy them.

This will vary depending on how many services you deploy, what size and how many of each task you run, and which region you deploy to.

**For general guidance only.** Origin Security's own telemetry pipeline implementation costs around USD $800/month to run in the Sydney region and manages around 400,000,000 events/day with regular peaks exceeding 10,000 events/second.

## Getting Started

Review the [documentation](/docs/README.md) for how to get started.

## License

This code to help you build the required AWS infrastructure, and Logstash sample configuration files, is licensed under the MIT license; Logstash itself is not.

Refer to [https://github.com/elastic/logstash/blob/master/LICENSE.txt](https://github.com/elastic/logstash/blob/master/LICENSE.txt) for details on Logstash's license.
