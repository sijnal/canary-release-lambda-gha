import json

def lambda_handler(event, context):
    # Simula un error con un código 400
    return {
        "statusCode": 400,
        "body": json.dumps({
            "message": "Simulated error for testing EventBridge rule."
        })
    }
