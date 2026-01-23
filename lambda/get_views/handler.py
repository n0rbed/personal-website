import json
import boto3
import os

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("TABLE_NAME", "PWebsiteStats"))

def lambda_handler(event, context):
    """
    Get the current view count from DynamoDB.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        dict: API Gateway response with view count
    """
    try:
        response = table.get_item(Key={"stats": "views"})
        count = int(response.get("Item", {}).get("count", 0))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"views": count})
        }
    except Exception as e:
        print(f"Error getting views: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": "Failed to retrieve views"})
        }