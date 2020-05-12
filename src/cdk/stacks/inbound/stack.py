import os
from aws_cdk import (
    core, 
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elb2,
    aws_iam as iam,
    aws_logs as cwl,
    aws_servicediscovery as awssd,
    aws_route53 as r53,
    aws_route53_targets as r53_targets,
    aws_secretsmanager as sm,
    aws_kinesis as ks
    )


class LogstashInStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, ctx: object, ecr_repository: ecr.Repository, kinesis_stream: ks.Stream, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.ecr_repository = ecr_repository

        self.vpc = ec2.Vpc.from_vpc_attributes(
            self, "VPC",
            **ctx.vpc_props.dict()
        )

        # CloudWatch Logs Group
        self.log_group = cwl.LogGroup(
            scope = self,
            id = "logs"
        )

        self.kinesis_stream = kinesis_stream

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


        # Load Balancer for Listening Services
        self.load_balancer = elb2.NetworkLoadBalancer(
            scope = self,
            id = f"{id}-nlb",
            vpc = self.vpc,
            internet_facing = False,
            cross_zone_enabled = True
        )

        # Create listener services
        service_names = []
        for service_name in getattr(ctx.inbound.services, "nlb", []):
            self.__create_nlb_service(service_name[0], ctx)
            service_names.append(service_name[0])
            
        for service_name in getattr(ctx.inbound.services, "cloudmap", []):
            self.__create_cloudmap_service(service_name[0], ctx)
            service_names.append(service_name[0])

        for service_name in getattr(ctx.inbound.services, "pull", []):
            self.__create_pull_service(service_name[0], ctx)
            service_names.append(service_name[0])

        service_names_output = core.CfnOutput(
            scope=self,
            id="service-names-out",
            value=",".join(service_names),
            export_name=f"{id}-service-names"
        )

    # Method to create a new Fargate service behind an existing load balancer
    def __create_nlb_service(self, service_name: str, ctx: object):
        ctx_srv = getattr(ctx.inbound.services.nlb, service_name)

        ecs_task_role = self.__create_default_task_role(service_name)

        log_driver = ecs.LogDriver.aws_logs(
            log_group = self.log_group,
            stream_prefix = service_name)

        # create a Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            scope = self,
            id = f"{service_name}_task_definition",
            cpu = ctx_srv.size.cpu,
            memory_limit_mib = ctx_srv.size.ram,
            execution_role = self.ecs_exec_role,
            task_role = ecs_task_role,
        )

        # create a container definition and associate with the Fargate task
        container_vars = self.__get_container_vars(service_name, ctx, ctx_srv)
        container = ecs.ContainerDefinition(
            scope = self,
            id = f"{service_name}_container_definition",
            task_definition = task_definition,
            image = ecs.ContainerImage.from_ecr_repository(self.ecr_repository, "latest"),
            logging = log_driver,
            **container_vars
        )
        security_group = ec2.SecurityGroup(
            scope = self,
            id = f"{service_name}_sg",
            vpc = self.vpc
        )
        service = ecs.FargateService(
            scope = self,
            id = f"{service_name}_service",
            task_definition = task_definition,
            cluster = self.cluster,
            desired_count = getattr(ctx_srv, "desired_count", ctx.default_desired_count),
            service_name = service_name,
            security_group = security_group,
            health_check_grace_period = core.Duration.minutes(10)
        )

        # map ports on the container
        for port in ctx_srv.ports:
            container.add_port_mappings(
                ecs.PortMapping(
                    container_port = port,
                    host_port = port,
                    protocol = ecs.Protocol.TCP
                )
            )
            # add a listener to network load balancer
            listener = self.load_balancer.add_listener(
                id = f"{service_name}_{port}",
                port = port
            )

            security_group.add_ingress_rule(
                ec2.Peer.ipv4(ctx.ingress_cidr),
                ec2.Port.tcp(port), f"Logstash ingress for {service_name}"
                )

            target = (service).load_balancer_target(
                container_name = container.container_name,
                container_port = port
            )

            listener.add_targets(
                id = f"{service_name}_{port}_tg",
                port = port,
                targets = [target]
            )

        scaling = service.auto_scale_task_count(
            max_capacity = ctx_srv.scaling.max_capacity,
            min_capacity = ctx_srv.scaling.min_capacity
        )

        scaling.scale_on_cpu_utilization(
            id = "cpu_scaling",
            target_utilization_percent = ctx_srv.scaling.target_utilization_percent,
            scale_in_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_in_cooldown_seconds),
            scale_out_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_out_cooldown_seconds)
        )

    def __create_cloudmap_service(self, service_name: str, ctx: object):
        ctx_srv = getattr(ctx.inbound.services.cloudmap, service_name)

        ecs_task_role = self.__create_default_task_role(service_name)

        log_driver = ecs.LogDriver.aws_logs(
            log_group = self.log_group,
            stream_prefix = service_name)

        # create a Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            scope = self,
            id = f"{service_name}_task_definition",
            cpu = ctx_srv.size.cpu,
            memory_limit_mib = ctx_srv.size.ram,
            execution_role = self.ecs_exec_role,
            task_role = ecs_task_role,
        )

        # create a container definition and associate with the Fargate task
        container_vars = self.__get_container_vars(service_name, ctx, ctx_srv)
        container = ecs.ContainerDefinition(
            scope = self,
            id = f"{service_name}_container_definition",
            task_definition = task_definition,
            image = ecs.ContainerImage.from_ecr_repository(self.ecr_repository, "latest"),
            logging = log_driver,
            **container_vars
        )
        security_group = ec2.SecurityGroup(
            scope = self,
            id = f"{service_name}_sg",
            vpc = self.vpc
        )
        service = ecs.FargateService(
            scope = self,
            id = f"{service_name}_service",
            task_definition = task_definition,
            cluster = self.cluster,
            desired_count = getattr(ctx_srv, "desired_count", ctx.default_desired_count),
            service_name = service_name,
            security_group = security_group
        )

        for port in ctx_srv.ports:
            container.add_port_mappings(
                ecs.PortMapping(
                    container_port = port,
                    host_port = port,
                    protocol = ecs.Protocol.TCP
                )
            )
            security_group.add_ingress_rule(
                ec2.Peer.ipv4(ctx.ingress_cidr),
                ec2.Port.tcp(port), f"Logstash ingress for {service_name}"
            )

        for port in ctx_srv.udp_ports:
            container.add_port_mappings(
                ecs.PortMapping(
                    container_port = port,
                    host_port = port,
                    protocol = ecs.Protocol.UDP
                )
            )
            security_group.add_ingress_rule(
                ec2.Peer.ipv4(ctx.ingress_cidr),
                ec2.Port.udp(port), f"Logstash ingress for {service_name}"
            )

        scaling = service.auto_scale_task_count(
            max_capacity = ctx_srv.scaling.max_capacity,
            min_capacity = ctx_srv.scaling.min_capacity
        )

        scaling.scale_on_cpu_utilization(
            id = "cpu_scaling",
            target_utilization_percent = ctx_srv.scaling.target_utilization_percent,
            scale_in_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_in_cooldown_seconds),
            scale_out_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_out_cooldown_seconds)
        )

        cloudmap = awssd.PublicDnsNamespace.from_public_dns_namespace_attributes(
            scope = self,
            id = f"cloudmap_namespace",
            **ctx.inbound.namespace_props.dict()
        )

        service.enable_cloud_map(
            cloud_map_namespace = cloudmap,
            dns_record_type = awssd.DnsRecordType("A"),
            dns_ttl = core.Duration.seconds(15)
        )

    def __create_pull_service(self, service_name: str, ctx: object):
        ctx_srv = getattr(ctx.inbound.services.pull, service_name)

        ecs_task_role = self.__create_default_task_role(service_name)

        log_driver = ecs.LogDriver.aws_logs(
            log_group = self.log_group,
            stream_prefix = service_name)

        # create a Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            scope = self,
            id = f"{service_name}_task_definition",
            cpu = ctx_srv.size.cpu,
            memory_limit_mib = ctx_srv.size.ram,
            execution_role = self.ecs_exec_role,
            task_role = ecs_task_role,
        )

        # create a container definition and associate with the Fargate task
        container_vars = self.__get_container_vars(service_name, ctx, ctx_srv)
        container = ecs.ContainerDefinition(
            scope = self,
            id = f"{service_name}_container_definition",
            task_definition = task_definition,
            image = ecs.ContainerImage.from_ecr_repository(self.ecr_repository, "latest"),
            logging = log_driver,
            **container_vars
        )
        security_group = ec2.SecurityGroup(
            scope = self,
            id = f"{service_name}_sg",
            vpc = self.vpc
        )
        service = ecs.FargateService(
            scope = self,
            id = f"{service_name}_service",
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
            scale_out_cooldown = core.Duration.seconds(ctx_srv.scaling.scale_out_cooldown_seconds)
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
            "AWS_REGION": ctx.aws_region
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

    def __create_default_task_role(self, service_name):
        ecs_task_role = iam.Role(
            scope = self,
            id = f"{service_name}_task_role",
            assumed_by = iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )
        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                actions = ["cloudwatch:PutMetricData"],
                effect = iam.Effect.ALLOW,
                resources = ["*"]
            ))
        self.kinesis_stream.grant_write(ecs_task_role)

        return ecs_task_role
