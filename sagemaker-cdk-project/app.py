#!/usr/bin/env python3
import aws_cdk as cdk
from sagemaker_cdk_project.sagemaker_cdk_project_stack import SageMakerProcessingStack

app = cdk.App()
SageMakerProcessingStack(app, "SageMakerProcessingStack",
    env=cdk.Environment(account='', region='us-east-1')
)
app.synth()

