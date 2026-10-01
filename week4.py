import boto3
import uuid

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

# --- Part A: EC2 Instance ---
sg_name = 'web-server-sg'
try:
    sgs = ec2_client.describe_security_groups(GroupNames=[sg_name])
    sg_id = sgs['SecurityGroups'][0]['GroupId']
except Exception:
    vpcs = ec2_client.describe_vpcs()
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    sg_res = ec2_client.create_security_group(
        GroupName=sg_name,
        Description='Security group for web server lab',
        VpcId=vpc_id
    )
    sg_id = sg_res['GroupId']
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )

key_pairs = ec2_client.describe_key_pairs()
key_names = [k['KeyName'] for k in key_pairs.get('KeyPairs', [])]
key_name = 'vockey' if 'vockey' in key_names else (key_names[0] if key_names else None)

user_data_script = """#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd"""

launch_kwargs = {
    'ImageId': 'ami-0fef201115eefe936',
    'MinCount': 1,
    'MaxCount': 1,
    'InstanceType': 't2.nano',
    'SecurityGroupIds': [sg_id],
    'UserData': user_data_script,
    'TagSpecifications': [{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': 'Web server'}]}]
}

if key_name:
    launch_kwargs['KeyName'] = key_name

new_instances = ec2.create_instances(**launch_kwargs)
inst = new_instances[0]

print("Launching EC2 instance...")
inst.wait_until_running()
inst.reload()
print("Instance Running.")
print("Instance ID:", inst.id)

# --- Part B: S3 Static Website ---
unique_bucket_name = f"site-{uuid.uuid4().hex[:8]}"

s3.create_bucket(Bucket=unique_bucket_name)

# Turn off Block Public Access for this bucket
s3_client.delete_public_access_block(Bucket=unique_bucket_name)

# Enable Static Website Hosting
website_configuration = {
    'ErrorDocument': {'Key': 'error.html'},
    'IndexDocument': {'Suffix': 'index.html'},
}
bucket_website = s3.BucketWebsite(unique_bucket_name)
bucket_website.put(WebsiteConfiguration=website_configuration)

print(f"\nS3 Bucket Created: {unique_bucket_name}")
print("Upload an index.html file to test it works!")
print(f"Bucket Endpoint: http://{unique_bucket_name}.s3-website-us-east-1.amazonaws.com")
