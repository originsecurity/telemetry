#!/bin/bash

# This bootstrap script is used to perfom find/replace in Logstash configuration files on start up.
# Some plugins (including azure event hubs) don't consistently process environment variables on startup, these can be substituted in here instead.

# sed -i -e 's|<<STORAGE_CONNECTION_SECRET>>|'"${STORAGE_CONNECTION_SECRET}"'|g' /usr/share/logstash/pipeline/40-azure_event_hubs.conf
# sed -i -e 's|<<AUDIT_LOGS_SECRET>>|'"${AUDIT_LOGS_SECRET}"'|g' /usr/share/logstash/pipeline/40-azure_event_hubs.conf
# sed -i -e 's|<<SIGN_IN_LOGS_SECRET>>|'"${SIGN_IN_LOGS_SECRET}"'|g' /usr/share/logstash/pipeline/40-azure_event_hubs.conf
# sed -i -e 's|<<AUDIT_LOGS_STATE_CONTAINER>>|'"${AUDIT_LOGS_STATE_CONTAINER}"'|g' /usr/share/logstash/pipeline/40-azure_event_hubs.conf
# sed -i -e 's|<<SIGN_IN_LOGS_STATE_CONTAINER>>|'"${SIGN_IN_LOGS_STATE_CONTAINER}"'|g' /usr/share/logstash/pipeline/40-azure_event_hubs.conf
logstash
