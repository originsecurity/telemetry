#!/usr/bin/env python3
import json
from aws_cdk import core
from tools.context import get_context
from stacks.ecr import ECRStack
from stacks.inbound.stack import LogstashInStack
from stacks.outbound.stack import LogstashOutStack
from stacks.queue.stack import LogstashQueueStack

app = core.App()
ctx = get_context(app.node)
env_core = core.Environment(account = ctx.account_id, region = ctx.aws_region)

logstash_queue = LogstashQueueStack(
    scope = app,
    id = f"{ctx.stage}-telemetry-logstash-queue",
    ctx = ctx,
    description = "Telemetry: Kinesis buffer queue for pipeline",
    env = env_core
)

logstash_in_ecr = ECRStack(
    scope = app,
    id = f"{ctx.stage}-telemetry-logstash-in-ecr",
    description = "Telemetry: ECR for inbound pipeline",
    env = env_core
)

logstash_in = LogstashInStack(
    scope = app,
    id = f"{ctx.stage}-telemetry-logstash-in",
    ctx = ctx,
    ecr_repository = logstash_in_ecr.ecr_repository,
    kinesis_stream = logstash_queue.kinesis_stream,
    description = "Telemetry: Logstash for inbound pipeline",
    env = env_core
)

logstash_out_ecr = ECRStack(
    scope = app,
    id = f"{ctx.stage}-telemetry-logstash-out-ecr",
    description = "Telemetry: ECR for outbound pipeline",
    env = env_core
)

logstash_out = LogstashOutStack(
    scope = app,
    id = f"{ctx.stage}-telemetry-logstash-out",
    ctx = ctx,
    ecr_repository = logstash_out_ecr.ecr_repository,
    kinesis_stream = logstash_queue.kinesis_stream,
    state_table = logstash_queue.state_table,
    description = "Telemetry: Logstash for outbound pipeline",
    env = env_core
)

app.synth()