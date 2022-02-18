import json
# import os
# print(os.listdir('/opt/'))
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
    # b=s3://async-athena-query/athena-query-result/a5dee61b-379e-4740-a05a-54df15383679.csv
    # b.split('/') => ['s3:', '', 'async-athena-query', 'athena-query-result', 'a5dee61b-379e-4740-a05a-54df15383679.csv']
    
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
    
    presigned_url=create_presigned_url(bucket,object)
    
    print(presigned_url)
    
    response={}
    # response['statusCode']=200
    response['Status']=status
    tmp={}
    response['QueryResult']=tmp
    response['QueryResult']['PresignedUrl']=presigned_url
    response['QueryResult']['ExpiredIn']=3600
    print(response)
    
    # payload_str = urllib.parse.urlencode(response, safe=':/?+%=&')
    
    # r = requests.post(callback_url, data=payload_str)
    
    r = requests.post(callback_url, data=json.dumps(response))
    print(r)
    
    return response

def create_presigned_url(bucket_name, object_name, expiration=3600):
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