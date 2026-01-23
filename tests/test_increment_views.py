import json
import pytest
import boto3
from moto import mock_aws
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["DYNAMODB_TABLE_NAME"] = "PWebsiteStats"


@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='PWebsiteStats',
            KeySchema=[{'AttributeName': 'stats', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'stats', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        table.put_item(Item={'stats': 'views', 'count': 0})
        yield dynamodb


@pytest.fixture
def lambda_dynamodb_class(dynamodb_table):
    from increment_views.handler import LambdaDynamoDBClass

    lambda_dynamodb_resource = {
        "resource": dynamodb_table,
        "table_name": "PWebsiteStats"
    }
    return LambdaDynamoDBClass(lambda_dynamodb_resource)


class TestIncrementCol:

    def test_increment_from_zero(self, lambda_dynamodb_class):
        from increment_views.handler import increment_col

        response = increment_col(lambda_dynamodb_class, "views", "count")
        body = json.loads(response["body"])
        assert body["views"] == 1

    def test_increment_multiple_times(self, lambda_dynamodb_class):
        from increment_views.handler import increment_col

        for i in range(1, 6):
            response = increment_col(lambda_dynamodb_class, "views", "count")
            body = json.loads(response["body"])
            assert body["views"] == i

    def test_increment_returns_correct_headers(self, lambda_dynamodb_class):
        from increment_views.handler import increment_col

        response = increment_col(lambda_dynamodb_class, "views", "count")
        assert response["headers"]["Content-Type"] == "application/json"
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_increment_nonexistent_item(self, dynamodb_table):
        from increment_views.handler import increment_col, LambdaDynamoDBClass

        dynamo_class = LambdaDynamoDBClass({
            "resource": dynamodb_table,
            "table_name": "PWebsiteStats"
        })

        response = increment_col(dynamo_class, "new_stat", "count")
        body = json.loads(response["body"])
        assert body["views"] == 1

    def test_increment_different_column(self, dynamodb_table):
        from increment_views.handler import increment_col, LambdaDynamoDBClass

        table = dynamodb_table.Table("PWebsiteStats")
        table.put_item(Item={'stats': 'downloads', 'total': 0})

        dynamo_class = LambdaDynamoDBClass({
            "resource": dynamodb_table,
            "table_name": "PWebsiteStats"
        })

        response = increment_col(dynamo_class, "downloads", "total")
        body = json.loads(response["body"])
        assert body["views"] == 1


class TestLambdaDynamoDBClass:

    def test_initialization(self, dynamodb_table):
        from increment_views.handler import LambdaDynamoDBClass

        dynamo_class = LambdaDynamoDBClass({
            "resource": dynamodb_table,
            "table_name": "PWebsiteStats"
        })

        assert dynamo_class.table is not None

    def test_table_access(self, lambda_dynamodb_class):
        response = lambda_dynamodb_class.table.get_item(Key={'stats': 'views'})
        assert response['Item']['count'] == 0


class TestLambdaHandler:

    def test_lambda_handler_success(self, aws_credentials):
        from increment_views.handler import lambda_handler

        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.create_table(
                TableName='PWebsiteStats',
                KeySchema=[{'AttributeName': 'stats', 'KeyType': 'HASH'}],
                AttributeDefinitions=[{'AttributeName': 'stats', 'AttributeType': 'S'}],
                BillingMode='PAY_PER_REQUEST'
            )

            table.put_item(Item={'stats': 'views', 'count': 0})

            response = lambda_handler({}, {})
            body = json.loads(response["body"])
            assert body["views"] == 1


class TestErrorHandling:

    def test_increment_with_invalid_table(self, dynamodb_table):
        from increment_views.handler import increment_col, LambdaDynamoDBClass

        dynamo_class = LambdaDynamoDBClass({
            "resource": dynamodb_table,
            "table_name": "NonExistentTable"
        })

        response = increment_col(dynamo_class, "views", "count")
        assert response["statusCode"] == 500


class TestIntegration:

    def test_full_lambda_workflow(self, dynamodb_table):
        from increment_views.handler import increment_col, LambdaDynamoDBClass

        dynamo_class = LambdaDynamoDBClass({
            "resource": dynamodb_table,
            "table_name": "PWebsiteStats"
        })

        r1 = increment_col(dynamo_class, "views", "count")
        r2 = increment_col(dynamo_class, "views", "count")

        assert json.loads(r1["body"])["views"] == 1
        assert json.loads(r2["body"])["views"] == 2
