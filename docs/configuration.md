# Configuration

1. [Service Types](service_types.md)
1. Configuration File Format (HERE)
1. [Getting Started Guide](getting_started.md)
1. [Logstash How-to and Tips](logstash.md)


All services are configured in `cdk.context.json`.

This file contains:

* Top level node called `shared` - where properties that are shared across stages are configured.
* Top level node called `{stage_name}` (eg `nonprod`, `prod`) for each stage.
  * This is where stage-specific settings are set.
  * You *can* override settings that are already set in the `shared` node here.

The `shared` and `{stage_name}` nodes for a given stage are _merged together_ when the cdk app is synthesised.

**The CDK app will only systhesise templates for one stage at a time.** The stage is selected specified by appending `--context stage=stage_name` to the `cdk synth` command.

Where settings exist in both `shared` and `{stage_name}`, the setting from stage-specific node will win. This lets you override any default settings specified under `shared`.

## Configuration Tree Structure

When merged, these nodes form a tree:
| Root | Branch/Leaf       | Branch/Leaf           | Description |
| -:   | -:                | :-                    | :-          |
| `┌`  | `debug_output`    |                       | Sets the DEBUG_OUTPUT environment variable referenced by the Logstash docker images. |
| `├`  | `account_id`      |                       | The AWS account that the stage to be deployed to. |
| `├`  | `aws_region`      |                       | The AWS region that the stacks will be deployed to. |
| `├`  | `secrets_key_arn` |                       | [OPTIONAL] The ARN of the customer-managed KMS key that is for encrypting secrets. |
| `├`  | `vpc_props`       |                       | This represents a dictionary whose settings are unpacked (`**`) directly into the vpc CDK constructor, referencing an _existing_ VPC and subnets. |
| `├`  | `inbound`         |                       | All settings related to inbound services. |
| `│`  | `├`               | `namespace_props`     | This represents a dictionary whose settings are unpacked (`**`) directly into the CloudMap CDK constructor, referencing an _existing_ CloudMap namespace. |
| `│`  | `└`               | `services`            | Fargate services are defined here. See **services nodes** description below. |
| `├`  | `queue`           |                       | All settings related to Kinesis. |
| `│`  | `├`               | `kinesis_endpoint`    | The VPC endpoint DNS name for connecting to Kinesis. |
| `│`  | `└`               | `kinesis_shard_count` | Number of shards to provision for the Kinesis data stream. |
| `└`  | `outbound`        |                       | All settings related to outbound services. |
|      | `└`               | `services`            | Fargate services are defined here. See **services nodes** description below. |

## Services nodes

The services structure is used in both inbound and outbound services:
| Root       | Branch/Leaf      | Branch/Leaf | Branch/Leaf | Leaf | Description |
| -:         | -:               | -:          | -:          | :-   | :-          |
| `services` |                  |             |             |      |             |
| `└`        | `{service_type}` | | | | The type of service: `nlb`, `cloudmap`, or `pull`. See [service types](service_types.md). |
|            | `└`              | `{service_name}` | | | The name of the service.<br>**Must be unique within the service's own ECS cluster.** |
|            |                  | `├`              | `desired_count` | | [OPTIONAL] The initial desired count setting for the service |
|            |                  | `├`              | `ports` | | [OPTIONAL] The TCP ports to listen on. |
|            |                  | `├`              | `udp_ports` | | [OPTIONAL] The UDP ports to listen on. |
|            |                  | `├`              | `size`          | | The size of the tasks within the service. |
|            |                  | `│`              | `├`             | `cpu` | See [AWS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html) for allowed values. |
|            |                  | `│`              | `└`             | `ram` | See [AWS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html) for allowed values. |
|            |                  | `├`              | `scaling`       | | . |
|            |                  | `│`              | `├`             | `min_capacity` | The minimum number of tasks that auto-scaling can scale-in to. |
|            |                  | `│`              | `├`             | `max_capacity` | The minimum number of tasks that auto-scaling can scale-out to. |
|            |                  | `│`              | `├`             | `target_utilization_percent` | The % CPU utilisation that auto-scaling will attempt to maintain for the service. |
|            |                  | `│`              | `├`             | `scale_in_cooldown_seconds` | The number of seconds since the last auto-scaling event before a scale-in (reduction in task count) can occur. |
|            |                  | `│`              | `└`             | `scale_out_cooldown_seconds` | The number of seconds since the last auto-scaling event before a scale-out (increase in task count) can occur.  |
|            |                  | `├`              | `secrets`       | | Dictionary `{}` of `key` : `value` pairs. <br>These will populate secrets from Secrets Manager into the named environment variable at container launch. |
|            |                  | `│`              | `└`             | `{"k":"v","k":"v"}` | `k`: The name of the environment variable to set. <br>`v`: The ARN of the AWS Secrets Manager secret. <br>**NOTE**: The string "_SECRET" is automatically appended to these variable names to avoid naming conflicts with non-secret variables below. All variable names are converted to uppercase. |
|            |                  | `└`              | `variables`     | | Dictionary `{}` of `key` : `value` pairs. |
|            |                  |                  | `└`             | `{"k":"v","k":"v"}` | `k`: The name of the environment variable to set. <br>`v`: The value to set. <br>**NOTE**: End S3 bucket variable names with the magic string "_log_bucket" and the Fargate task will be granted write permissions to that bucket. All variable names are converted to uppercase.|

## Temporarily disabling services

To disable a service set all three of its `desired_count`, `scaling.min_capacity`, **and** `scaling.max_capacity` values to `0`.