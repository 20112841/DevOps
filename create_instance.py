import boto3

ec2 = boto3.resource('ec2')
ec2_client = boto3.client('ec2')

# 1. Manage Security Group (HTTP 80 & SSH 22)
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
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )

# 2. Key Pair Selection
key_pairs = ec2_client.describe_key_pairs()
key_names = [k['KeyName'] for k in key_pairs.get('KeyPairs', [])]
key_name = 'vockey' if 'vockey' in key_names else (key_names[0] if key_names else None)

# 3. User Data Script (Installs Apache)
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
    'TagSpecifications': [
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Web server'
                }
            ]
        }
    ]
}

if key_name:
    launch_kwargs['KeyName'] = key_name

# 4. Launch Instance
new_instances = ec2.create_instances(**launch_kwargs)
inst = new_instances[0]

print("Launched Instance ID:", inst.id)
print("Waiting for instance to reach running state...")
inst.wait_until_running()
inst.reload()

print("Instance State:", inst.state['Name'])
print("Public IP Address:", inst.public_ip_address)
