import boto3
import json
from botocore.exceptions import ClientError

def get_secret():

    secret_name = "rds!db-b6160ecf-5de6-4e8b-b6ff-4abccb70a585"
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = response['SecretString']

    # ✅ Convert JSON string → Python dictionary
    return json.loads(secret)