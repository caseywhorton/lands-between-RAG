import aws_cdk as core
import aws_cdk.assertions as assertions

from sagemaker_cdk_project.sagemaker_cdk_project_stack import SagemakerCdkProjectStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sagemaker_cdk_project/sagemaker_cdk_project_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SagemakerCdkProjectStack(app, "sagemaker-cdk-project")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
