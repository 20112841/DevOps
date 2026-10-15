#!/usr/bin/bash

# Fetch Instance ID 
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)

# Collect metrics
MEMORY_USAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2}')
PROCESS_COUNT=$(ps -e --no-headers | wc -l)

# Check Apache status
if systemctl is-active --quiet httpd; then
    WEB_STATUS="RUNNING"
else
    WEB_STATUS="NOT RUNNING"
fi

# Print report

echo "==============================="
echo "       MONITORING STATS        "
echo "==============================="
echo "Instance ID      : $INSTANCE_ID"
echo "Memory Utilisation: $MEMORY_USAGE"
echo "No of processes  : $PROCESS_COUNT"
echo "Web Server Status: $WEB_STATUS"
