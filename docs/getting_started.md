# Getting Started

1. [Service Types](service_types.md)
1. [Configuration File Format](configuration.md)
1. Getting Started Guide (HERE)
1. [Logstash How-to and Tips](logstash.md)


Familiarise yourself with the available [service types](service_types.md) and [configuration file format](configuration.md) first.

This getting started guide will help you deploy a basic logging pipeline, that listens for Elastic beats events, and archives those events to a pre-existing S3 bucket.

## Synthesize CloudFormation templates

1. Make sure you've installed [Python 3](https://www.python.org/downloads/), [AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html), [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html), and [setup credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).
    * We need these for converting the Python CDK code to native CloudFormation, and for uploading Logstash Docker images to ECR.
1. If you haven't, install [Docker](https://docs.docker.com/get-docker/)
    * This is needed for building the Logstash images, before we upload them to ECR.
1. In a new python/conda environment, install any dependencies with `pip install -r requirements.txt` from the root of the repo.
1. Change to the cdk source directory `cd src/cdk`
1. Modify the `src/cdk/EXAMPLE-cdk.context.json` file to:
    1. Find and replace all instances of `ap-southeast-2` with your preferred AWS region.
    1. Replace `stage_name` with the unique name to call this instance of the pipeline (e.g. `nonprod`, `prod`, `test`, `uat`)
    1. Update `account_id` with your AWS account ID.
    1. Update `vpc_props` with the VPC ID, AZs, and subnet IDs that you want to deploy to.
    1. Replace `beats-bucket-name` with the name of the pre-existing S3 bucket that you want Logstash to archive beats events to.
    1. Replace `catchall-bucket-name` with the name of the pre-existing S3 bucket that you want Logstash to archive unknown event sources to.
    1. [OPTIONAL] Update `stage_name`.`queue`.`kinesis_endpoint` with your Kinesis Data Streams VPC Endpoint.
    1. [OPTIONAL] Update `stage_name`.`queue`.`kinesis_shard_count` to accommodate your expected peak event load.
        * See [Determining the Initial Size of a Kinesis Data Stream](https://docs.aws.amazon.com/streams/latest/dev/amazon-kinesis-streams.html)
1. Rename `src/cdk/EXAMPLE-cdk.context.json` to `src/cdk/cdk.context.json`
1. Run `cdk synth --context stage=stage_name`
    * Replace `stage_name` with the name of the stage, eg. `prod` or `nonprod`.
    * This needs to match an existing stage name in config file.

## Deploy ECR Stacks and build Docker images

1. [Create](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html) the `src/cdk/cdk.out/{stage_name}-telemetry-logstash-in-ecr.template.json` CloudFormation stack in your account.
1. When complete, click the `Resources` tab on the CloudFormation stack in the AWS console.
1. Click the physical ID of the newly created ECR repo - this links directly to the ECR console.
    * This value is also outputted as a stack _output_ for use in an automated CI/CD pipeline.
1. In the ECR console click `View push commands`
1. Change directory to `src/docker/logstash-in`
1. Follow ECR push instructions with one minor change:
    * Append `--build-arg LOGSTASH_VERSION=7.x.x` to the `docker build` command. Replace 7.x.x with your preferred and tested Logstash version.
    * e.g. `docker build -t prod1-abcde-xxxxxxxxxxxxx . --build-arg LOGSTASH_VERSION=7.6.2`
`
1. Repeat these steps for the outbound stack and image
    * **Stack:** `src/cdk/cdk.out/{stage_name}-telemetry-logstash-out-ecr.template.json`
    * **Image directory:** `src/docker/logstash-out`

## Deploy Logging Pipeline Stacks

1. **Kinesis / Queue:**
    * [Create](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html) the `src/cdk/cdk.out/{stage_name}-telemetry-logstash-queue.template.json` CloudFormation stack in your account.
1. **Logstash Outbound / Processor:**
    * [Create](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html) the `src/cdk/cdk.out/{stage_name}-telemetry-logstash-out.template.json` CloudFormation stack in your account.
1. **Logstash Inbound:**
    * [Create](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html) the `src/cdk/cdk.out/{stage_name}-telemetry-logstash-in.template.json` CloudFormation stack in your account.

## Next Steps

* Customise the `cdk.context.json` to suit your needs - take a look at `src/cdk/EXAMPLE-ADVANCED-cdk.context.json` for additional ideas. The advanced config file provides examples for all three types of service, and shows how you would configure multiple stages (`nonprod` and `prod`) in the same file.
* Customise the `logstash-in` image to add support for any new log sources you need and modify `logstash-out` to better process and parse events from Syslog sources.
