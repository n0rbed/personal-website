# -----------------------------
# DynamoDB Table
# -----------------------------

resource "aws_dynamodb_table" "website_stats" {
  name         = "PWebsiteStats"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "stats"

  attribute {
    name = "stats"
    type = "S"
  }
}

# -----------------------------
# Initialize table manually or use this
# -----------------------------

resource "null_resource" "initialize_table" {
  depends_on = [aws_dynamodb_table.website_stats]

  provisioner "local-exec" {
    command = <<-EOT
      aws dynamodb put-item \
        --table-name ${aws_dynamodb_table.website_stats.name} \
        --item '{"stats": {"S": "views"}, "count": {"N": "0"}}' \
        --condition-expression "attribute_not_exists(stats)" || true
    EOT
  }
}

# -----------------------------
# IAM Roles
# -----------------------------

resource "aws_iam_role" "get_views_role" {
  name = "GetViewsLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "get_views_policy" {
  name = "GetViewsPolicy"
  role = aws_iam_role.get_views_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.website_stats.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "increment_views_role" {
  name = "IncrementViewsLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "increment_views_policy" {
  name = "IncrementViewsPolicy"
  role = aws_iam_role.increment_views_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.website_stats.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------
# Lambda Functions (from external files)
# -----------------------------

data "archive_file" "get_views_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/get_views"
  output_path = "${path.module}/get_views.zip"
}

resource "aws_lambda_function" "get_views" {
  filename      = data.archive_file.get_views_zip.output_path
  function_name = "GetWebsiteViews"
  role          = aws_iam_role.get_views_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  timeout       = 5

  source_code_hash = data.archive_file.get_views_zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.website_stats.name
    }
  }
}

data "archive_file" "increment_views_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/increment_views"
  output_path = "${path.module}/increment_views.zip"
}

resource "aws_lambda_function" "increment_views" {
  filename      = data.archive_file.increment_views_zip.output_path
  function_name = "IncrementWebsiteViews"
  role          = aws_iam_role.increment_views_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.10"
  timeout       = 5

  source_code_hash = data.archive_file.increment_views_zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.website_stats.name
    }
  }
}

# -----------------------------
# API Gateway (HTTP API)
# -----------------------------

resource "aws_apigatewayv2_api" "http_api" {
  name          = "WebsiteViewsApi"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "get_views_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.get_views.invoke_arn

  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "increment_views_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.increment_views.invoke_arn

  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_views_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "GET /views"
  target    = "integrations/${aws_apigatewayv2_integration.get_views_integration.id}"
}

resource "aws_apigatewayv2_route" "increment_views_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /views"
  target    = "integrations/${aws_apigatewayv2_integration.increment_views_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "allow_api_invoke_get" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_views.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
}

resource "aws_lambda_permission" "allow_api_invoke_post" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.increment_views.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*"
}

# -----------------------------
# Outputs
# -----------------------------

output "api_endpoint" {
  description = "Base URL for the API"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}
