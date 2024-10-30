import boto3

from cpr_sdk.search_adaptors import VespaSearchAdapter


def get_aws_ssm_param(param_name: str, region_name: str = "eu-west-1") -> str:
    """Retrieve a parameter from AWS SSM"""
    ssm = boto3.client("ssm", region_name=region_name)
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_vespa_search_adapter_from_aws_secrets(
    cert_dir: str,
    vespa_instance_url_param_name: str = "VESPA_INSTANCE_URL",
    vespa_public_cert_param_name: str = "VESPA_PUBLIC_CERT",
    vespa_private_key_param_name: str = "VESPA_PRIVATE_KEY",
) -> VespaSearchAdapter:
    """
    Get a VespaSearchAdapter instance by retrieving secrets from AWS Secrets Manager.

    We then save the secrets to local files in the cert_dir directory and instantiate
    the VespaSearchAdapter.
    """
    vespa_instance_url = get_aws_ssm_param(vespa_instance_url_param_name)
    vespa_public_cert = get_aws_ssm_param(vespa_public_cert_param_name)
    vespa_private_key = get_aws_ssm_param(vespa_private_key_param_name)

    with open(f"{cert_dir}/cert.pem", "w") as f:
        f.write(vespa_public_cert)
    with open(f"{cert_dir}/key.pem", "w") as f:
        f.write(vespa_private_key)

    return VespaSearchAdapter(instance_url=vespa_instance_url, cert_directory=cert_dir)
