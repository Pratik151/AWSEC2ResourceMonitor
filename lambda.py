import boto3
import base64
import gzip
import json
import base64

DEFAULT_THRESHOLD_VALUE = 90.0
DEFAULT_TEAM_VALUE = 'defaultTeam'

def create_sns_topic(topic_name, region):
    client = boto3.client('sns', region_name=region)
    response = client.create_topic(Name=topic_name)
    return response

def get_ec2_tags(ec2_instanceId, region):
    ec2 = boto3.resource('ec2', region_name=region)
    thresholdValue = None
    teamValue = None
    ec2instance = ec2.Instance(ec2_instanceId)
    print(ec2_instanceId)
    print(ec2instance)
    all_tags = ec2instance.tags
    if all_tags is None:
        return (None, None)

    for tag in all_tags:
        if tag['Key'] == 'Threshold':
            thresholdValue = tag['Value']
        if tag['Key'] == 'Team':
            teamValue = tag['Value']

    return (thresholdValue, teamValue)

def create_cloudwatch_alarm(instance_id, thresholdValue, teamValue, region):
    sns_create_response = create_sns_topic(teamValue, region)
    print(sns_create_response)
    sns_topic_arn = sns_create_response['TopicArn']
    cloudwatch = boto3.client('cloudwatch', region_name=region)
    # Create alarm
    cloudwatch_response = cloudwatch.put_metric_alarm(
            AlarmName='CPU_Monitor_' + instance_id,
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=1,
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Period=60,
            Statistic='Average',
            Threshold=float(thresholdValue),
            AlarmActions=[sns_topic_arn],
            AlarmDescription='Alarm when server CPU exceeds 70%',
            Dimensions=[
                {
                  'Name': 'InstanceId',
                'Value': instance_id
                },
            ]        
        )
    print(cloudwatch_response)

def lambda_handler(event, context):
    # TODO implement
    print(event)
    thresholdValue = DEFAULT_THRESHOLD_VALUE
    teamValue = DEFAULT_TEAM_VALUE
    cw_data = event['awslogs']['data']
    #print(f'data: {cw_data}')
    #print(f'type: {type(cw_data)}')
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    logEvents = payload['logEvents']
    #print(logEvents)
    for event in logEvents:
        message = event['message']
        #print(event)
        message = json.loads(message)
        print(message['eventName'])
        if message['eventName'] == 'RunInstances':
            region = message['awsRegion']
            instance_id = message['responseElements']['instancesSet']['items'][0]['instanceId']
            thresholdValue, teamValue = get_ec2_tags(instance_id, region)
            if thresholdValue is None:
                thresholdValue = DEFAULT_THRESHOLD_VALUE
            if teamValue is None:
                teamValue = DEFAULT_TEAM_VALUE
            create_cloudwatch_alarm(instance_id, thresholdValue, teamValue, region)

        elif message['eventName'] == 'TerminateInstances':
            region = message['awsRegion']
            instance_id = message['responseElements']['instancesSet']['items'][0]['instanceId']
            cloudwatch = boto3.client('cloudwatch', region_name=region)
            alarm_name = 'CPU_Monitor_' + instance_id
            response = cloudwatch.delete_alarms(
                AlarmNames=[
                    alarm_name
                    ]
                )
            print(response)
        '''
        if event['source'] == 'aws.tag':
            print('Processing event for aws.tag')
            instance_id = event['resources'][0].split('/')[-1]        
            changed_tags = event['detail']['changed-tag-keys']
            for tag in changed_tags:
                if tag == 'Threshold':

                    # If Threshold tag is not in 'tags' dictionary it means tag was deleted 
                    # and we update alarm value back to default
                    if 'Threshold' in event['detail']['tags'].keys():
                        thresholdValue = event['detail']['tags']['Threshold']
                if tag == 'Team':
                    if 'Team' in event['detail']['tags'].keys():
                        teamValue = event['detail']['tags']['Team']

                print('Updating alarm for tag change event for instance: ' + instance_id)
                create_cloudwatch_alarm(instance_id, thresholdValue, teamValue)
                print('Processing completed for aws.tag event')
        '''

    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }
