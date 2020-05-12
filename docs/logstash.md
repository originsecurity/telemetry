# Logstash How-to and Tips

1. [Service Types](service_types.md)
1. [Configuration File Format](configuration.md)
1. [Getting Started Guide](getting_started.md)
1. Logstash How-to and Tips (HERE)

## Monitoring

Several useful metrics are pushed every minute to CloudWatch by the Logstash healthcheck pipeline in both the inbound and outbound images.

Search CloudWatch metrics for `Telemetry/stage_name` to find various event metrics and JVM stats from Logstash itself.

Because logstash event metrics continue increasing over time while logstash is running, use the CloudWatch `RATE()` function to transform this into the rate of change per second as a proxy for events per second. For example, this CloudWatch metric expression will return the events per second inbound across all service types: `SUM(RATE(SEARCH('Telemetry Inbound EventsIn', 'Maximum', 60)))`.

## Inbound

For `logstash-in` one image is used for all of the different inbound tasks. This makes image patching and management easier and helps avoid sprawl.
Logstash will dynamically switch config file on startup based on the `LOGSTASH_CONF` environment variable (see line `6` of `src/docker/logstash-in/config/pipelines.yml` for how this is done).

To setup Logstash for a new inbound source:

1. Create a new `.conf` file under the `src/docker/logstash-in/pipelines/` folder
1. Create your inbound service in the CDK [configuration file](configuration.md).
1. Ensure that the CDK service has a `logstash_conf` variable set with the value as the name of the config file.
1. For `nlb` and `cloudmap` services, update the inbound Dockerfile (`src/docker/logstash-in/Dockerfile`) to make sure you `EXPOSE` any newly required ports.

### TIP: Load Balancing Syslog

Load balancing syslog can be difficult, especially when receiving very large volumes of events from a small number of devices (e.g.firewalls). This is because the Network Load Balancer doesn't balance our syslog event load, it balances _new inbound connections_.

If you have two Fargate tasks (`"min_capacity":2` / `"max_capacity":2`) behind the load balancer handling inbound requests, with one device sending a torrent of data, with the other device sending a trickle, you can end up with one Fargate task running hot, while the other one sits practically idle.

If you _scale out_ to cope with the load, you'll now have a third task sitting idle while the original problem remains. Syslog requires a careful balance between _scaling up_ by giving your tasks more CPU and _scaling out_ by running more capacity.

If anticipating higher event counts (thousands per second), consider running multiple different types of inbound Syslog services, for different types of devices (high volume network devices _vs_ low volume apps), running on different ports.

## Outbound

The `logstash-out` image uses the Logstash pipeline-to-pipeline [distributor pattern](https://www.elastic.co/guide/en/logstash/current/pipeline-to-pipeline.html#distributor-pattern).

To enable Syslog or Azure Event Hubs samples, or to add a new source:

1. Add the new pipeline or uncomment the sample pipeline in `src/docker/logstash-out/config/pipelines.yml`
1. Add a new if statement or uncomment the sample if statement in `src/docker/logstash-out/pipelines/00-parent.conf`
    * This is the distributor pipeline that splits off different types of event to specialised processing pipelines.
    * Avoid adding any unnecessary logic or filtering in the parent pipeline.

### TIP: Syslog Parsing

When managing a large number of different types of devices, from different vendors understand that:

1. You will quickly need more processor nodes, as this activity is CPU intensive.
    * The outbound pipeline supports auto scaling in and out to handle load very well.
    * Consider adding more CPU only if you start needing to scale out to many tasks as this better optimises for the overhead of Logstash itself.
1. Grok patterns can very quickly get very messy.
    * Put complex patterns in an external patterns file under `src/docker/logstash-out/patterns`. 
    * Reference these with the [patterns_dir](https://www.elastic.co/guide/en/logstash/current/plugins-filters-grok.html#plugins-filters-grok-patterns_dir) option (e.g. `patterns_dir => "/usr/share/logstash/patterns"`).

## Pushing Updates

Once you have updated your Logstash configuration files, you need to:

1. Re-build your Docker images
1. Push the updated images up to their respective ECR repositories
1. Tell ECS it needs to deploy the updated image for each service (log source).
    * Use the [`aws ecs update-service` command](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/ecs/update-service.html)
    * To re-deploy the outbound processor service
        * `aws ecs update-service --service processor --cluster YOUR_OUTBOUND_CLUSTER_NAME_HERE --force-new-deployment'`
    * To re-deploy the inbound beats service
        * `aws ecs update-service --service beats --cluster YOUR_INBOUND_CLUSTER_NAME_HERE --force-new-deployment'`

Consider building this process into an automated deployment pipeline to automatically push updated when you make a change to your Logstash configuration file code.
