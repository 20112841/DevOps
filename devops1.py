import boto3

ec2 = boto3.resource('ec2')
for inst in ec2.instances.all():
    print("EC2 Instance ID:", inst.id, "Public IP:", inst.public_ip_address)

s3 = boto3.resource('s3')
for bucket in s3.buckets.all():
    print("S3 Bucket Name:", bucket.name)
