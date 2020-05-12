import os
from aws_cdk import (
    core, 
    aws_dynamodb as ddb,
    aws_ec2 as ec2, 
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_logs as cwl,
    aws_secretsmanager as sm,
    aws_kinesis as ks,
    )


class LogstashOutStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, ctx: object, ecr_repository: ecr.Repository, kinesis_stream: ks.Stream, state_table: ddb.Table, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.ecr_repository = ecr_repository
        self.kinesis_stream = kinesis_stream
        self.state_table = state_table
        service_name = "processor"
        ctx_srv = getattr(ctx.outbound.services.pull, service_name)

        self.vpc = ec2.Vpc.from_vpc_attributes(
            self, "VPC",
            **ctx.vpc_props.dict()
        )

        # CloudWatch Logs Group
        self.log_group = cwl.LogGroup(
            scope = self,
            id = "logs"
        )

        # Create a new ECS cluster for our services
        self.cluster = ecs.Cluster(
            self,
            vpc = self.vpc,
            id = f"{id}_cluster"
        )
        cluster_name_output = core.CfnOutput(
            scope=self,
            id="cluster-name-out",
            value=self.cluster.cluster_name,
            export_name=f"{id}-cluster-name"
        )

        service_names_output = core.CfnOutput(
            scope=self,
            id="service-names-out",
            value=service_name,
            export_name=f"{id}-service-names"
        )
        
        # Create a role for ECS to interact with AWS APIs with standard permissions
        self.ecs_exec_role = iam.Role(
            scope = self,
            id = "ecs_logstash-exec_role",
            assumed_by = iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies = ([
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy")
            ])
        )
        # Grant ECS additional permissions to decrypt secrets from Secrets Manager that have been encrypted with our custom key
        if getattr(ctx, "secrets_key_arn", None) is not None:
            self.ecs_exec_role.add_to_policy(
                iam.PolicyStatement(
                    actions = ["kms:Decrypt"],
                    effect = iam.Effect.ALLOW,
                    resources = [ctx.secrets_key_arn]
                ))
        # Grant ECS permissions to log to our log group
        self.log_group.grant_write(self.ecs_exec_role)

        # Create a task role to grant permissions for Logstash to interact with AWS APIs
        ecs_task_role = iam.Role(
            scope = self,
            id = f"{service_name}_task_role",
            assumed_by = iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )
        # Add permissions for Logstash to send metrics to CloudWatch
        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                actions = ["cloudwatch:PutMetricData"],
                effect = iam.Effect.ALLOW,
                resources = ["*"]
            ))
        # Add permissions for Logstash to interact with our Kinesis queue
        self.kinesis_stream.grant_read(ecs_task_role)
        # Remove this when next version of kinesis module is released
        # https://github.com/aws/aws-cdk/pull/6141
        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                actions = ["kinesis:ListShards"],
                effect = iam.Effect.ALLOW,
                resources = [self.kinesis_stream.stream_arn]
            ))
        # Add permissions for Logstash to store Kinesis Consumer Library (KCL) state tracking in DynamoDB
        state_table.grant_full_access(ecs_task_role)
        # Add permissions for Logstash to upload logs to S3 for archive
        bucket_resources = []
        for k, v in ctx_srv.variables.items():
            if k.endswith("_log_bucket"):
                bucket_resources.append('arn:aws:s3:::{0}'.format(v))
                bucket_resources.append('arn:aws:s3:::{0}/*'.format(v))
        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:PutObject",
                    "s3:ListMultipartUploadParts",
                    "s3:ListBucket",
                    "s3:AbortMultipartUpload"
                    ],
                effect=iam.Effect.ALLOW,
                resources=bucket_resources
            ))

        # Task Definition
        task_definition = ecs.FargateTaskDefinition(
            scope = self,
            id = f"{service_name}_task_definition",
            cpu = ctx_srv.size.cpu,
            memory_limit_mib = ctx_srv.size.ram,
            execution_role = self.ecs_exec_role,
            task_role = ecs_task_role,
        )

        log_driver = ecs.LogDriver.aws_logs(
            log_group = self.log_group,
            stream_prefix = service_name)
        
        # Container Definition
        container_vars = self.__get_container_vars(service_name, ctx, ctx_srv)
        container = ecs.ContainerDefinition(
            scope = self,
            id = f"{service_name}_container_definition",
            task_definition = task_definition,
            image = ecs.ContainerImage.from_ecr_repository(self.ecr_repository, "latest"),
            logging = log_driver,
            **container_vars
        )

        # Service Definition
        security_group = ec2.SecurityGroup(
            scope = self,
            id = f"{service_name}_sg",
            vpc = self.vpc
        )

        service = ecs.FargateService(
            scope = self,
            id = f"{service_name}_fargate_service",
            task_definition = task_definition,
            cluster = self.cluster,
            desired_count = getattr(ctx_srv, "desired_count", ctx.default_desired_count),
            service_name = service_name,
            security_group = security_group
        )

        scaling = service.auto_scale_task_count(
            max_capacity = ctx_srv.scaling.max_capacity,
            min_capacity = ctx_srv.scaling.min_capacity
        )

        scaling.scale_on_cpu_utilization(
            id = "cpu_scaling",
            target_utilization_percent = ctx_srv.scaling.target_utilization_percent,
            scale_in_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_in_cooldown_seconds),
            scale_out_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_out_cooldown_seconds),
        )

    def __get_container_vars(self, service_name, ctx, ctx_srv):
        # Prepare container defaults
        container_vars = {}
        container_environment = {
            "ENV_STAGE": ctx.stage,
            "SERVICE_NAME": service_name,
            "DEBUG_OUTPUT": ctx.debug_output,
            "LS_JAVA_OPTS": "-Xms256m -Xmx{0}m".format(ctx_srv.size.ram - 256),
            "KINESIS_ENDPOINT": ctx.queue.kinesis_endpoint,
            "KINESIS_STREAM_NAME": self.kinesis_stream.stream_name,
            "AWS_REGION": ctx.aws_region,
            "DYNAMODB_STATE_TABLE_NAME": self.state_table.table_name
            }
        container_secrets = {}

        # Get and populate service-specific variables and secrets from context
        if hasattr(ctx_srv, "variables"):
            for k, v in ctx_srv.variables.items():
                container_environment[k.upper()] = v
        if hasattr(ctx_srv, "secrets"):
            for k, v in ctx_srv.secrets.items():
                sm_secret = sm.Secret.from_secret_arn(
                    scope = self, 
                    id = f"{k}-secret", 
                    secret_arn = v
                )
                ecs_secret = ecs.Secret.from_secrets_manager(sm_secret)                    
                secret_env_key = "{0}_SECRET".format(k.upper())
                container_secrets[secret_env_key] = ecs_secret
        
        if container_environment:
            container_vars["environment"] = container_environment
        if container_secrets:
            container_vars["secrets"] = container_secrets

        return container_vars