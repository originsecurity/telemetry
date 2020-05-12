import os
from aws_cdk import (
    core,
    aws_dynamodb as ddb,
    aws_kinesis as ks
    )

class LogstashQueueStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, ctx: object, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Kinesis Data Stream for telemetry buffer
        self.kinesis_stream = ks.Stream(
            scope = self,
            id = "logstash_queue",
            shard_count = ctx.queue.kinesis_shard_count
        )
        self.state_table = ddb.Table(
            scope = self,
            id = "logstash_state",
            partition_key = ddb.Attribute(name="leaseKey", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=core.RemovalPolicy.DESTROY
        )
