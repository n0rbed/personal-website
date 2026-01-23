import json
import pytest
from moto import mock_aws
import boto3
import os
import sys

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['TABLE_NAME'] = 'PWebsiteStats'


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mocked DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='PWebsiteStats',
            KeySchema=[{'AttributeName': 'stats', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'stats', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        table.put_item(Item={'stats': 'views', 'count': 42})
        yield table


def test_get_views_success(dynamodb_table):
    """Test successful retrieval of view count."""
    from get_views.handler import lambda_handler  # moved import here

    event = {}
    context = {}

    response = lambda_handler(event, context)

    assert response['statusCode'] == 200
    assert 'body' in response

    body = json.loads(response['body'])
    assert body['views'] == 42

    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    assert response['headers']['Content-Type'] == 'application/json'


def test_get_views_no_data(aws_credentials):
    """Test when no view count exists."""
    from get_views.handler import lambda_handler  # moved import here

    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        dynamodb.create_table(
            TableName='PWebsiteStats',
            KeySchema=[{'AttributeName': 'stats', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'stats', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        event = {}
        context = {}

        response = lambda_handler(event, context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['views'] == 0
