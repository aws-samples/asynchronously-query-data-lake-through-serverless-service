import json
import requests
import boto3
from botocore.exceptions import ClientError

import urllib.parse

def lambda_handler(event, context):
    # print(event)
    # print(event['ApiRequest']['CallbackUrl'])
    # print(event['AthenaResult']['QueryExecution']['ResultConfiguration']['OutputLocation'])
    
    callback_url=event['ApiRequest']['CallbackUrl']
    file=event['AthenaResult']['QueryExecution']['ResultConfiguration']['OutputLocation']
    status=event['AthenaResult']['QueryExecution']['Status']
    
    obj_array=file.split('/')
    bucket=file.split('/')[2]
    
    obj=''
    for i in range(len(obj_array)):
        if (i>2):
            obj=obj+'/'+obj_array[i]
    
    object=obj[1:]

    print('Bucket: {}'.format(bucket))
    print('Object: {}'.format(object))
    
    print('s3 presign url for downloading query result: ')
    
    presignedUrl_expiration_time=3600
    presigned_url=create_presigned_url(bucket,object,presignedUrl_expiration_time)
    
    print(presigned_url)
    
    response={}

    response['Status']=status
    tmp={}
    response['QueryResult']=tmp
    response['QueryResult']['PresignedUrl']=presigned_url
    response['QueryResult']['ExpiredIn']=presignedUrl_expiration_time
    print(response)
    
    r = requests.post(callback_url, data=json.dumps(response))
    print(r.status_code)
    
    return response

def create_presigned_url(bucket_name, object_name, expiration):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        print(e)
        return None

    # The response contains the presigned URL
    return response