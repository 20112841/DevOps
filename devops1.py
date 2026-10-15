import boto3
import sys
import subprocess
import random
import string
import time

ssm = boto3.client('ssm')
param = ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')
ami_id = param['Parameter']['Value']

ec2 = boto3.resource('ec2')

#STEP 3 - USER DATA SCRIPT

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

#STEP 1 + 2 -- LAUNCH AND CONFIGURE EC2 INSTANCE

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
instance.wait_until_running()
instance.reload()

#STEP 7 -- AMI CREATION

timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%f")
ami_name = f"df-{timestamp}"

print(f"Creating AMI: {ami_name}...")
image = instance.create_image(
    Name=ami_name,
    Description="AMI created from DevOps web server instance"
)
print(f"AMI ID: {image.id}")

ec2_url = f"http://{instance.public_ip_address}"
print("Instance ID:", instance.id)
print("Public IP Address:", instance.public_ip_address)
print(f"Web Server URL: {ec2_url}")

#STEP 4 -- SET UP WEBSITE AND BUCKET

random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
bucket_name = f"{random_chars}-dfoley"
print(f"Creating S3 bucket: {bucket_name}...")

s3_resource = boto3.resource('s3', region_name='us-east-1')
s3_client = boto3.client('s3', region_name='us-east-1')

try:
    response = s3_resource.create_bucket(Bucket=bucket_name)
    print(response)
except Exception as error:
    print(error)

image_url = "http://devops.setudemo.net/logo.jpg"
image_filename = "logo.jpg"

try:
    subprocess.run(["curl", "-s", "-o", image_filename, image_url], check=True)
except subprocess.CalledProcessError as e:
    print(f"Failed to download the image from {image_url}. Error: {e}")
    sys.exit(1)

html_content = f"""<html>
<body>
<h1>S3 Static Website</h1>
<img src="{image_filename}" alt="Logo">
</body>
</html>"""

with open("index.html", "w") as f:
    f.write(html_content)

s3_client.upload_file(image_filename, bucket_name, image_filename, ExtraArgs={'ContentType': 'image/jpeg'})
s3_client.upload_file("index.html", bucket_name, "index.html", ExtraArgs={'ContentType': 'text/html'})

s3_client.put_public_access_block(
    Bucket=bucket_name,
    PublicAccessBlockConfiguration={
        'BlockPublicAcls': False,
        'IgnorePublicAcls': False,
        'BlockPublicPolicy': False,
        'RestrictPublicBuckets': False
    }
)

public_policy = f"""{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::{bucket_name}/*"]
        }}
    ]
}}"""

s3_client.put_bucket_policy(
    Bucket=bucket_name,
    Policy=public_policy
)

bucket_website = s3_resource.BucketWebsite(bucket_name)
bucket_website.put(
    WebsiteConfiguration={
        'IndexDocument': {'Suffix': 'index.html'}
    }
)

print("S3 bucket successfully configured for static website hosting!")
s3_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
print(f"Website URL: {s3_url}")

#STEP 5 -- WRITE BOTH URLS TO A FILE

with open("dfoley-websites.txt", "w") as f:
    f.write(f"EC2 Web Server URL: {ec2_url}\n")
    f.write(f"S3 Static Website URL: {s3_url}\n")
    
print("Both URLs successfully written to file")

#STEP 6 -- MONITORING

time.sleep(30)

subprocess.run([
    "scp",
    "-i", "aws.pem",
    "monitoring.sh",
    f"ec2-user@{instance.public_ip_address}:/home/ec2-user/"
], check=True)

subprocess.run([
    "ssh",
    "-i", "aws.pem",
    f"ec2-user@{instance.public_ip_address}",
    "chmod +x monitoring.sh && ./monitoring.sh"
], check=True)
