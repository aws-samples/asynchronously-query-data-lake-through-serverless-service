## Asynchronously Query Data Lake through Serverless Service
In this sample we will show you how to query your data lake through serverless service which includes Step Function and Lambda. 

![image1](https://user-images.githubusercontent.com/17841922/154645497-401d4933-d70e-4e72-93f8-65655a9ba078.png)
1. User send request to API Gateway and trigger StepFunction to orchestrate Athena to query and check result is ready
    * The request might look like:
    ```
    {
        "Query": "SELECT \"col1\", \"col2\" FROM \"database1\".\"tableA\" limit 10",
        "CallbackUrl": "https://test.api"
    }
    ```
    * The response look like:
    ```
    {
        "executionArn": "your-execution-arn",
        "startDate": 1.645062485009E9
    }
    ```

2. Lambda to generate the presign URL and post the result to callback URL
    ```
    {
        "State": {
            "CompletionDateTime": 1645062487295,
            "State": "SUCCEEDED | FAILED | CANCELLED",
            "SubmissionDateTime": 1645062485193
        }
        "QueryResult": {
            "PresignedUrl": "https://xxxx/query-results-path/yyy.csv",
            "ExpiredIn": 3600
        }
    }
    ```

You can follow the guide as following:

### Create Lambda from sample code
* Create a Lambda which you can reference the sample code in python: [async-athena-query-callbacker.py](lambda/async-athena-query-callbacker.py)
* You need to make sure your Lambda have permission to execute S3 related operation.
    * The execution role's permission look like:
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": "arn:aws:s3:::*"
            }
        ]
    }
    ```
    * Trust relationship look like:
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    ```

### Create a Step Function from json
* Create a Step Function from json, which you need to replace `<your-lambda-function-arn>` in [AthenaQueryOrchestration.json](stepfunction/AthenaQueryOrchestration.json) with the lambda arn you just create. And create Step Fucntion from this json file.
    * In your Step Function we call the Athena to start execution with parameter:
    ```
    ...
    "Parameters": {
        "QueryString.$": "$.Query",
        "WorkGroup": "primary"
    }
    ...
    ```
    You need to make sure WorkGroup: primary already with default query result output location, or pass it through Parameter ResultConfiguration.OutputLocation, for more detail information you can reference [API_StartQueryExecution](https://docs.aws.amazon.com/athena/latest/APIReference/API_StartQueryExecution.html).
* Creat new role when setting permissions for execution role which let Step Functions create a new role for you based on your state machine's definition and configuration details.

### Create API Gateway from swagger
* Create a API Gateway from swagger, which you need to replace `<your-execution-role>` in [AsyncAthenaQueryEntry-swagger.json](apigateway-swagger/AsyncAthenaQueryEntry-swagger.json) with IAM role which provide API gateway to start execution StepFunctions. Also replace `<your-state-machine-arn>` with StepFunction arn you just created. And then create API Gateway from the swagger json file.
    * For the `<your-execution-role>`, you need to make sure your API Gateway have permission to call Step Function and start execution.
    * The execution role's permission look like:
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "states:*",
                "Resource": "*"
            }
        ]
    }
    ```
    * Trust relationship look like:
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "apigateway.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    ```
* Test it with Postman and provide IAM key and secret which with API Gateway permission in AWS signature.


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

