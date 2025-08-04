import boto3
import os

def handler(event, context):
    print("Event received:", event)
    sm = boto3.client('sagemaker')

    try:
        response = sm.create_processing_job(
            ProcessingJobName=f"rag-processing-job-{context.aws_request_id}",
            RoleArn=os.environ['SAGEMAKER_ROLE_ARN'],
            ProcessingResources={
                "ClusterConfig": {
                    "InstanceCount": 1,
                    "InstanceType": "ml.m5.xlarge",
                    "VolumeSizeInGB": 30
                }
            },
            AppSpecification={
                "ImageUri": os.environ['IMAGE_URI']
            },
            Environment={
                "PINECONE_API_KEY": os.environ['PINECONE_API_KEY'],
                "INDEX_NAME": os.environ['INDEX_NAME'],
                "S3_BUCKET_NAME": os.environ['S3_BUCKET_NAME'],
                "S3_PREFIX": os.environ['S3_PREFIX']
            },
            StoppingCondition={"MaxRuntimeInSeconds": 3600}
        )

        print("Started processing job:", response)
        return {"status": "Job Started", "response": response}

    except Exception as e:
        print("Error starting processing job:", str(e))
        return {"status": "Failed", "error": str(e)}
