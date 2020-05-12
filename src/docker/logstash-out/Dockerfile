ARG LOGSTASH_VERSION
FROM docker.elastic.co/logstash/logstash:${LOGSTASH_VERSION}

USER root 

RUN yum erase -y java-11-openjdk java-11-openjdk-devel java-11-openjdk-headless \
    && rpm --import https://yum.corretto.aws/corretto.key \
    && curl -L -o /etc/yum.repos.d/corretto.repo https://yum.corretto.aws/corretto.repo \
    && yum install -y java-1.8.0-amazon-corretto-devel \
    && yum clean all \
    && rm -rf /var/cache/yum


COPY ./config/ /usr/share/logstash/config/
COPY ./pipelines/ /usr/share/logstash/pipeline
COPY ./patterns/ /usr/share/logstash/patterns/

RUN logstash-plugin install logstash-input-http_poller \
    logstash-output-stdout \
    logstash-output-cloudwatch \
    logstash-output-s3 \
    logstash-output-syslog \
    logstash-output-tcp \
    logstash-output-kinesis \
    logstash-input-kinesis

ENTRYPOINT [ "logstash" ]
