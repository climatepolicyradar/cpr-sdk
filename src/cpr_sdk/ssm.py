import boto3


def get_aws_ssm_param(param_name: str, region_name: str = "eu-west-1") -> str:
    """Retrieve a parameter from AWS SSM"""
    ssm = boto3.client("ssm", region_name=region_name)
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]
