ARG LOGSTASH_VERSION
FROM docker.elastic.co/logstash/logstash:${LOGSTASH_VERSION}

USER root 

RUN yum erase -y java-11-openjdk java-11-openjdk-devel java-11-openjdk-headless \
    && rpm --import https://yum.corretto.aws/corretto.key \
    && curl -L -o /etc/yum.repos.d/corretto.repo https://yum.corretto.aws/corretto.repo \
    && yum install -y java-1.8.0-amazon-corretto-devel \
    && yum clean all \
    && rm -rf /var/cache/yum


EXPOSE 514/tcp
EXPOSE 514/udp
EXPOSE 5044/tcp
EXPOSE 5514/tcp
EXPOSE 9600/tcp


COPY ./config/ /usr/share/logstash/config/
COPY ./pipelines/ /usr/share/logstash/pipeline/
COPY ./bootstrap.sh /bin/bootstrap.sh 


RUN chmod 755 /bin/bootstrap.sh \ 
    && logstash-plugin install \
    logstash-input-http_poller \
    logstash-input-azure_event_hubs \
    logstash-output-stdout \
    logstash-output-cloudwatch \
    logstash-output-kinesis 

ENTRYPOINT [ "/bin/bootstrap.sh"]

