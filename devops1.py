import boto3

ssm = boto3.client('ssm')
param = ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')
ami_id = param['Parameter']['Value']

ec2 = boto3.resource('ec2')
#automatically install and update apache and connect to it, use token to get metadata about instance
user_data_script = """#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd
TOKEN=`curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
AMI_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/ami-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
echo "<html><body>" > /var/www/html/index.html
echo "<h1>DevOps Web Server</h1>" >> /var/www/html/index.html
echo "<p>Instance ID: $INSTANCE_ID</p>" >> /var/www/html/index.html
echo "<p>Public IP Address: $PUBLIC_IP</p>" >> /var/www/html/index.html
echo "<p>AMI ID: $AMI_ID</p>" >> /var/www/html/index.html
echo "<p>Availability Zone: $AZ</p>" >> /var/www/html/index.html
echo "</body></html>" >> /var/www/html/index.html
"""
#create the instance 
instances = ec2.create_instances(
    ImageId=ami_id,
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.nano',
    Placement={'AvailabilityZone': 'us-east-1b'},
    KeyName='aws',
    SecurityGroups=['default'],
    UserData=user_data_script,
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': 'DevOpsAssignmentInstance'}
            ]
        }
    ]
)

instance = instances[0]
print("Launching instance...")
#waiter here until done loading and refresh and then grab info
instance.wait_until_running()
instance.reload()

#print instance info and web server address
print("Instance ID:", instance.id)
print("Public IP Address:", instance.public_ip_address)
print(f"Web Server URL: http://{instance.public_ip_address}")
