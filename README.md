# AWSEC2ResourceMonitorStack

# AWS Services used:

1. AWS Events Rule (For triggering events based on EC2 instance state change or tag change. )
2. AWS Lambda (As target to Event rules and to create/modify cloudwatch alarms.)
3. AWS Cloudwatch (For monitoring EC2 instance metric and alert to target based on threshold)
4. AWS SNS (As target to Cloudwatch alarm for notifying subscribers about alert) 
5. AWS StackSets (For creating the resource from cloudformation in multiple region or account as required.)


# Prerequisite:

For Stackset to deploy the resources in multiple regions/account it needs below two roles:

https://s3.amazonaws.com/cloudformation-stackset-sample-templates-us-east-1/AWSCloudFormationStackSetAdministrationRole.yml

https://s3.amazonaws.com/cloudformation-stackset-sample-templates-us-east-1/AWSCloudFormationStackSetExecutionRole.yml

Reference : https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs-self-managed.html


Service monitored: EC2
Resource monitored: CPUUtilization.

EC2 tags that controls threshold and team topic:
1. Threshold
2. Team

Default value: 
Threshold = 90
Team = defaultTeam

*defaultTeam topic is created as part of cloudformation stack creation.

Cloudformation template creates below resource:
1. AWS::IAM::Role (Logical id: CloudWatchCreateAlarmIAMRole):
   This role is attached to lambda with access to create/delete alarms, read EC2 data.

2. AWS::Lambda::Function (Logical id: CreateLambdaFunction)
   This lambda funnction is used to create/delete cloud watch alarms, SNS topics.

3. AWS::Events::Rule (Logical id: EC2InstanceEventRule and EC2TagChangeRule)
   This are used to invoke lambda function for EC2 state change or tag change events.

4. AWS::Lambda::Permission - Permission for event rule to trigger lambda functions.

5. AWS::SNS::Topic (logical id: defaultSNSTopic)
   Default SNS topic used when Team tag is not defined.

# Flow:

1. Whenever a new EC2 instance is created or tag is modified, AWS Event rules triggers lambda function.

2. Lambda function checks the type of event (EC2 state change or tag change) and based on that uses logic to create/modify/delete cloudwatch alarm. (file: lambda.py)

   -> If the instance state is running, it gets the EC2 tags and create cloud watch alarm based on that. (Default values are used if tag is not defined).
   -> If the instance state changes to delete, cloud watch alarm is deleted.
   -> If there is change in tag, checks are done to find the modified value. If tag is deleted the alarm values will be set back to default values.
   Alarm name used: CPU_Monitor_ + insstance_id
   
   For multiple region support, AWS Stackset will be used to create Stacks. https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
   
   I have validating by creating stack from Console UI. Equivalent CLI command: 
   
   ```aws cloudformation create-stack-set --stack-set-name EC2ResourceMonitorStackset --template-body file://EC2ResourceMonitorStack.json --description "Cloudformation stack for EC2 resource monitor stack" --regions '["us-east-1", "us-west-2"] --parameters  ParameterKey=DefaultTeamEmailParameter,ParameterValue=defaaultteam@gmail.com --permission-model SELF_MANAGED -administration-role-arn <AWSCloudFormationStackSetAdministrationRole role ARN> --execution-role-name AWSCloudFormationStackSetExecutionRole --accounts ["<account id1>","<account-id2>"]```
