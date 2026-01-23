import json
from boto3 import resource
from os import environ

_LAMBDA_DYNAMODB_RESOURCE = { "resource" : resource('dynamodb'), 
                              "table_name" : environ.get("DYNAMODB_TABLE_NAME","PWebsiteStats") }

class LambdaDynamoDBClass:
    """
    AWS DynamoDB Resource Class
    """
    def __init__(self, lambda_dynamodb_resource):
        """
        Initialize a DynamoDB Resource
        """
        self.resource = lambda_dynamodb_resource["resource"]
        self.table_name = lambda_dynamodb_resource["table_name"]
        self.table = self.resource.Table(self.table_name)          

def lambda_handler(event, context):
    """
    Increment the view count in DynamoDB.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        dict: API Gateway response with updated view count
    """
    global _LAMBDA_DYNAMODB_RESOURCE
    dynamodb_resource_class = LambdaDynamoDBClass(_LAMBDA_DYNAMODB_RESOURCE)
    return increment_col(dynamodb_resource_class, "views", "count")



def increment_col(dynamo_db: LambdaDynamoDBClass, key: str, col_to_increment: str):
    try:
        response = dynamo_db.table.update_item(
            Key={"stats": key},
            UpdateExpression="ADD #c :inc",
            ExpressionAttributeNames={"#c": col_to_increment},
            ExpressionAttributeValues={":inc": 1},
            ReturnValues="UPDATED_NEW"
        )

        new_count = int(response["Attributes"][col_to_increment])

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"views": new_count}) }
    except Exception as e:
        print(f"Error incrementing views: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": "Failed to increment views"})
        }
