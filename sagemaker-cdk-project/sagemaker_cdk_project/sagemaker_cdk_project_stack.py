from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    CfnOutput,
)
from constructs import Construct
import os

class SageMakerProcessingStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # Configuration
        account_id = self.account
        region = self.region
        
        # S3 Buckets
        embedding_bucket_name = ""
        evaluation_bucket_name = ""
        
        embedding_bucket = s3.Bucket.from_bucket_attributes(
            self, "EmbeddingBucket",
            bucket_name=embedding_bucket_name,  
            region=region
        )
        evaluation_bucket = s3.Bucket.from_bucket_name(
            self, "EvaluationBucket", evaluation_bucket_name
        )

        # Create SageMaker execution role
        sagemaker_role = iam.Role(
            self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
            ],
            inline_policies={
                "ECRAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:GetAuthorizationToken",
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )

        # Create SNS Topic for notifications
        notification_topic = sns.Topic(
            self, "SageMakerProcessingJobNotifications",
            display_name="SageMaker Processing Job Notifications"
        )
        notification_topic.add_subscription(subs.EmailSubscription("casey.whorton@gmail.com"))

        # Docker image URIs
        embedding_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/lambda-embedder:latest"
        evaluation_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/lambda-evaluate:latest"

        # Lambda execution role
        lambda_execution_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "SageMakerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sagemaker:CreateProcessingJob",
                                "sagemaker:DescribeProcessingJob"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["iam:PassRole"],
                            resources=[sagemaker_role.role_arn]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                f"arn:aws:s3:::{embedding_bucket_name}",
                                f"arn:aws:s3:::{embedding_bucket_name}/*",
                                f"arn:aws:s3:::{evaluation_bucket_name}",
                                f"arn:aws:s3:::{evaluation_bucket_name}/*"
                            ]
                        )
                    ]
                )
            }
        )

        # Lambda function for embedding processing job
        embedding_lambda = _lambda.Function(
            self, "TriggerEmbeddingSageMakerJob",
            function_name="trigger-embedding-sagemaker-job",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="lambda_embedding.handler",
            code=_lambda.Code.from_asset(os.path.join(os.getcwd(), "lambda")),
            role=lambda_execution_role,
            environment={
                "SAGEMAKER_ROLE_ARN": sagemaker_role.role_arn,
                "IMAGE_URI": embedding_image_uri,
                "PINECONE_API_KEY": "",
                "INDEX_NAME": "",
                "S3_BUCKET_NAME": embedding_bucket_name,
                "S3_PREFIX": "reddit_data/EldenringBuilds",
                "SNS_TOPIC_ARN": notification_topic.topic_arn
            },
            timeout=Duration.minutes(15),
            memory_size=512
        )

        # Grant SNS publish permissions
        notification_topic.grant_publish(embedding_lambda)

        # Lambda function for evaluation processing job
        evaluation_lambda = _lambda.Function(
            self, "TriggerEvaluationSageMakerJob",
            function_name="trigger-evaluation-sagemaker-job",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="lambda_evaluate.handler",
            code=_lambda.Code.from_asset(os.path.join(os.getcwd(), "lambda")),
            role=lambda_execution_role,
            environment={
                "SAGEMAKER_ROLE_ARN": sagemaker_role.role_arn,
                "IMAGE_URI": evaluation_image_uri,
                "OPENAI_API_KEY": "",
                "PINECONE_API_KEY": "",
                "INDEX_NAME": "",
                "S3_BUCKET_NAME": evaluation_bucket_name,
                "SNS_TOPIC_ARN": notification_topic.topic_arn
            },
            timeout=Duration.minutes(15),
            memory_size=512
        )

        # Grant SNS publish permissions
        notification_topic.grant_publish(evaluation_lambda)

        # S3 trigger for embedding Lambda (when new data arrives)
        embedding_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(embedding_lambda),
            s3.NotificationKeyFilter(prefix="reddit_data/EldenringBuilds/")
        )

        # EventBridge rule to trigger evaluation when embedding job completes
        embedding_completion_rule = events.Rule(
            self, "EmbeddingJobCompletionRule",
            rule_name="embedding-job-completion-trigger",
            description="Triggers evaluation job when embedding SageMaker job completes",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail_type=["SageMaker Processing Job State Change"],
                detail={
                    "ProcessingJobStatus": ["Completed"],
                    "ProcessingJobName": [{"prefix": "rag-processing-job"}]
                }
            )
        )

        # Add evaluation Lambda as target for the EventBridge rule
        embedding_completion_rule.add_target(
            targets.LambdaFunction(
                evaluation_lambda,
                event=events.RuleTargetInput.from_object({
                    "source": "eventbridge",
                    "detail_type": "embedding-job-completed",
                    "embedding_job_name": events.EventField.from_path("$.detail.ProcessingJobName"),
                    "embedding_job_status": events.EventField.from_path("$.detail.ProcessingJobStatus"),
                    "timestamp": events.EventField.from_path("$.time")
                })
            )
        )

        # EventBridge rule for evaluation job completion (for notifications)
        evaluation_completion_rule = events.Rule(
            self, "EvaluationJobCompletionRule",
            rule_name="evaluation-job-completion-notification",
            description="Sends notification when evaluation SageMaker job completes",
            event_pattern=events.EventPattern(
                source=["aws.sagemaker"],
                detail_type=["SageMaker Processing Job State Change"],
                detail={
                    "ProcessingJobStatus": ["Completed", "Failed"],
                    "ProcessingJobName": [{"prefix": "evaluation-processing-job"}]
                }
            )
        )

        # Add SNS topic as target for evaluation completion
        evaluation_completion_rule.add_target(
            targets.SnsTopic(
                notification_topic,
                message=events.RuleTargetInput.from_text(
                    f"Evaluation SageMaker job has completed.\n"
                    f"Job Name: {events.EventField.from_path('$.detail.ProcessingJobName')}\n"
                    f"Status: {events.EventField.from_path('$.detail.ProcessingJobStatus')}\n"
                    f"Time: {events.EventField.from_path('$.time')}"
                )
            )
        )

        # Outputs
        CfnOutput(
            self, "EmbeddingLambdaFunctionName",
            value=embedding_lambda.function_name,
            description="Name of the embedding trigger Lambda function"
        )

        CfnOutput(
            self, "EvaluationLambdaFunctionName", 
            value=evaluation_lambda.function_name,
            description="Name of the evaluation trigger Lambda function"
        )

        CfnOutput(
            self, "SNSTopicArn",
            value=notification_topic.topic_arn,
            description="ARN of the SNS notification topic"
        )

        CfnOutput(
            self, "SageMakerRoleArn",
            value=sagemaker_role.role_arn,
            description="ARN of the SageMaker execution role"
        )