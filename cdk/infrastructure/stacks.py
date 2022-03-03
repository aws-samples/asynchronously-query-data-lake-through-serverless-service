from aws_cdk import (
    Aws,
    Stack,
    CfnOutput,
    Duration,
    aws_stepfunctions as _sf,
    aws_stepfunctions_tasks as _tasks,
    aws_apigatewayv2 as _apigwv2,
    aws_lambda as _lambda,
    aws_iam as _iam,
)

from constructs import Construct

class AsyncQueryAthenaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._region = Aws.REGION
        self._account_id = Aws.ACCOUNT_ID

        self._fn = _lambda.Function(self, 'AsyncAthenaQueryCallback',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='async-athena-query-callbacker.lambda_handler',
            code=_lambda.Code.from_asset(
                path='lambda'
            ),
            timeout=Duration.minutes(3),
            memory_size=128,
            environment={
                'REGION': self._region,
                'ACCOUNT_ID': self._account_id
            },
        )

        #submit the query and wait for the results
        _start_query_task = _tasks.AthenaStartQueryExecution(
            self, 'Start Athena Query',
            query_string=_sf.JsonPath.string_at('$.Query'),
            result_selector={
                'QueryExecutionId.$': '$.QueryExecutionId'
            },
            result_path='$.AthenaRequest',
            input_path='$.ApiRequest',
            work_group='primary'
        )

        #get the results
        _query_results_task = _tasks.AthenaGetQueryResults(
            self, 'Get Query Results',
            result_selector={
                'QueryExecution.$': '$.QueryExecution'
            },
            query_execution_id=_sf.JsonPath.string_at('$.QueryExecution.QueryExecutionId'),
            result_path='$.AthenaResult',
            input_path='$.AthenaRequest',
        )

        # Invoke Lamnbda
        _invoke_lambda = _tasks.LambdaInvoke(
            self, 'InvokeLambda',
            lambda_function=self._fn,
            output_path='$.Payload',
            payload=_sf.TaskInput.from_json_path_at('$'),
            retry_on_service_exceptions=True,
        )

        # wait for period of time
        _wait = _sf.Wait(
            self, 'wait',
            time=_sf.WaitTime.duration(Duration.seconds(15))
        )

        # Check Query Status
        _check_query_status = _sf.Choice(self, 'Check Query Status').when(
            _sf.Condition.or_(
                _sf.Condition.string_equals(
                    '$.AthenaResult.QueryExecution.Status.State',
                    'SUCCEEDED'
                ),
                _sf.Condition.string_equals(
                    '$.AthenaResult.QueryExecution.Status.State',
                    'FAILED'
                ),
                _sf.Condition.string_equals(
                    '$.AthenaResult.QueryExecution.Status.State',
                    'CANCELLED'
                ),
            ), 
        _invoke_lambda).otherwise(_wait)

        # Step function workflow
        self._workflow = _sf.StateMachine(
            self, "AthenaQuery",
            definition=_start_query_task.
                next(_wait).
                next(_query_results_task).
                next(_check_query_status),
            # Max duration for Athean Query is 30 mins
            timeout=Duration.minutes(30),
        )

        self._api_role = self._create_apigw_to_stepfunction_start_exec_role()
        self._http_api = self._create_apigw_v2()
        self._stage = self._create_stage()
        self._route = self._create_stepfunction_start_exec_route()
    
        CfnOutput(self, 'StepFunctionArn',
            value = self._workflow.state_machine_arn,
            description = 'StepFunction Workflow Arn'
        )

        CfnOutput(self, 'HttpApiEndpoint', 
            description='HTTP API Endpoint', 
            value=self._http_api.attr_api_endpoint
        )

    def _create_apigw_v2(self):
        return _apigwv2.CfnApi(
            self,'AsyncQueryAthenaHttpApi',
            cors_configuration=_apigwv2.CfnApi.CorsProperty(
                allow_credentials=False,
                allow_headers=["*"],
                allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
                allow_origins=["*"],
                max_age=0,
            ),
            name='AsyncQueryAthenaHttpApi',
            protocol_type='HTTP'
        )

    def _create_stage(self):
        _stage = _apigwv2.CfnStage(self, 'HttpToSfStartExecStage',
            api_id=self._http_api.ref,
            stage_name='$default',
            auto_deploy=True
        )
        return _stage

    def _create_stepfunction_start_exec_route(self):
        _integ =_apigwv2.CfnIntegration(
            self, 'HttpToSfStartExecSubTypeInteg',
            api_id=self._http_api.ref,
            integration_type='AWS_PROXY',
            integration_subtype='StepFunctions-StartExecution',
            payload_format_version='1.0',
            request_parameters={
                'StateMachineArn': self._workflow.state_machine_arn,
                'Input': '$request.body.Input',
            },
            credentials_arn=self._api_role.role_arn,
        )
        return _apigwv2.CfnRoute(
            self, 'HttpApiStepfunctionStartExecRoute',
            api_id=self._http_api.ref,
            authorization_type='AWS_IAM',
            route_key='POST /startexec',
            target='/'.join(['integrations',_integ.ref]),
        )

    def _create_apigw_to_stepfunction_start_exec_role(self):
        _role = _iam.Role(
            self, 'ApiGwHttpApiSfStartExecRole',
            assumed_by=_iam.ServicePrincipal('apigateway.amazonaws.com')
        )

        _role.add_managed_policy(
            _iam.ManagedPolicy.from_managed_policy_arn(
                self, 'ApiGwPushCwPolicy',
                'arn:aws:iam::aws:policy/service-role/'\
                'AmazonAPIGatewayPushToCloudWatchLogs'
            )
        )
        _role.attach_inline_policy(
            _iam.Policy(
                self,
                'ApiGwHttpApiSfStartExecInlinePolicy',
                statements=[
                    _iam.PolicyStatement(
                        actions=[
                            'states:StartExecution',
                        ],
                        resources=[self._workflow.state_machine_arn]
                    )
                ]
            )
        )
        return _role
