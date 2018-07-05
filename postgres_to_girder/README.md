<head>
<style>
ol {
  counter-reset: item;
}
ol li {
  display: block;
}
ol li:before {
  content: counters(item, ".") ". ";
  counter-increment: item;
  position: relative;
  left: -2em;
}
</style>
</head>

# Mindlogger on AWS

## Prepare an AWS Account

> 1. If you don't already have an AWS account, create one at https://aws.amazon.com by following the on-screen instructions. Part of the sign-up process involves receiving a phone call and entering a PIN using the phone keypad.

&mdash; Amazon Web Services, Inc. (2018). [Step 1. Prepare an AWS Account](https://docs.aws.amazon.com/quickstart/latest/mongodb/step1.html). *MongoDB on AWS
MongoDB Quick Start*.

## Install and Configure Amazon Web Services Command Line Interface

### Install Example (Linux)

```bash
$ pip install awscli --upgrade --user
```

&mdash; Amazon Web Services, Inc. (2018). [Installing the AWS Command Line Interface](https://docs.aws.amazon.com/cli/latest/userguide/installing.html). *AWS Command Line Interface
User Guide*.

### Configure Example (Linux)

AWS Access Key ID and Secret Access Key available at
[https://console.aws.amazon.com/iam](https://console.aws.amazon.com/iam)/home?region=us-east-1#/users/``[username]``?section=security_credentials

```bash
$ aws configure
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-west-2
Default output format [None]: json
```
&mdash; Amazon Web Services, Inc. (2018). [Configuring the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html). *AWS Command Line Interface
User Guide*.

## Create an Amazon Elastic Compute Cloud (EC2) Key Pair

<blockquote><div id="main-content"><div id="main-col-body"><h1 class="topictitle" id="cfn-console-create-keypair">Creating an EC2 Key Pair</h1>
     <p>The use of some AWS CloudFormation resources and templates will require you to specify
        an Amazon EC2 key pair
        for authentication, such as when you are configuring SSH access to your instances.
     </p>
     <p>Amazon EC2 key pairs can be created with the AWS Management Console. For more information,
        see
        <a href="http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html" target="_blank">Amazon EC2 Key Pairs</a> in the
        <em>Amazon EC2 User Guide for Linux Instances</em>.
     </p>
  </div>
  <noscript>
     <div>
        <div>
           <div>
              <div id="js_error_message">
                 <p><img src="https://d1ge0kk1l5kms0.cloudfront.net/images/G/01/webservices/console/warning.png" alt="Warning" /> <strong>Javascript is disabled or is unavailable in your browser.</strong></p>
                 <p>To use the AWS Documentation, Javascript must be enabled. Please refer to your browser's
                    Help pages for instructions.
                 </p>
              </div>
           </div>
        </div>
     </div>
  </noscript>
</div>
</blockquote>

&mdash; Amazon Web Services, Inc. (2010). [Creating an EC2 Key Pair](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-keypair.html). *AWS CloudFormation
User Guide (API Version 2010-05-15)*.

### Example (Linux)
```bash
aws ec2 create-key-pair \
--key-name MindloggerGirder \
--query 'KeyMaterial' \
--output text > MindloggerGirder.pem
```

## Make SSH Key Private

Ie, owner can read; group and others have no access.

### Example (Linux)

```bash
$ chmod 400 MindloggerGirder.pem
```
## Deploy MongoDB Into a Virtual Private Cloud (VPC) on AWS

Follow the "Option 1" instructions in [Step 2. Launch the Quick Start](https://docs.aws.amazon.com/quickstart/latest/mongodb/step2.html):

<ol><li><a href="https://fwd.aws/Kxy33" target="_blank">
  <span class="inlinemediaobject">
    <img src="https://docs.aws.amazon.com/quickstart/latest/mongodb/images/launch-button-new.png" alt="Quick Start launch button for MongoDB in new VPC">
  </span>
</a></li>
<li><blockquote>
  <p>On the <b>Specify Details</b> page, change the stack name if
    needed. Review the parameters for the template. Provide values for the
    parameters that require your input. For all other parameters, review the default
    settings and customize them as necessary. When you finish reviewing and
    customizing the parameters, choose <b>Next</b>.
  </p><p>[. . .]</p>
  <p>&bull; <a href="step2.html#new">Parameters for deploying MongoDB into a new VPC</a></p>
</blockquote></li>

&mdash; Amazon Web Services, Inc. (2018). [Step 2. Launch the Quick Start](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-keypair.html). *MongoDB on AWS
MongoDB Quick Start*.

<ol><li>
<blockquote><em>Network Configuration:</em><table>
  <tbody><tr>
     <th>Parameter label</th>
     <th>Parameter name</th>
     <th>Default</th>
     <th>Description</th>
  </tr><tr>
     <td><b>Allowed Bastion External Access CIDR</b></td>
     <td>RemoteAccessCIDR</td>
     <td><em class="replaceable"><code class="">Requires input</code></em></td>
     <td>The CIDR IP range that is permitted external SSH access to the bastion hosts. We recommend that you set this value to a trusted IP range. For example, you might want to grant only your corporate network access to the software.</td>
  </tr></tbody>
</table></blockquote>

&mdash; Amazon Web Services, Inc. (2018). [Option 1: Parameters for deploying MongoDB into a new VPC](https://docs.aws.amazon.com/quickstart/latest/mongodb/step2.html#new). *MongoDB on AWS MongoDB Quick Start: Step 2. Launch the Quick Start*.

<blockquote>Specify the IPv6 address of your computer in CIDR notation. For example, if your IPv6 address is <code>2001:db8:1234:1a00:9691:9503:25ad:1761</code>, specify <code>2001:db8:1234:1a00:9691:9503:25ad:1761/128</code> to list the single IP address in CIDR notation. If your company allocates addresses from a range, specify the entire range, such as <code>2001:db8:1234:1a00::/64</code>.</blockquote>

&mdash; Amazon Web Services, Inc. (2018). [Adding a Rule for Inbound SSH Traffic to a Linux Instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/authorizing-access-to-an-instance.html#add-rule-authorize-access). *Amazon Elastic Compute Cloud
User Guide for Linux Instances: Authorizing Inbound Traffic for Your Linux Instances*.

</li>
<li><blockquote><em>Security Configuration:</em><div class="table">
  <p class="title"><b></b></p>
  <div class="table-contents">
     <table id="w151aac13c11b5b8c19">
        <tbody><tr>
           <th>Parameter label</th>
           <th>Parameter name</th>
           <th>Default</th>
           <th>Description</th>
        </tr>
        <tr>
           <td><b>Key Name</b></td>
           <td>KeyPairName</td>
           <td><em class="replaceable"><code class="">Requires input</code></em></td>
           <td>Public/private key pair, which allows you to connect securely
              to your instance after it launches. When you created an AWS
              account, this is the key pair you created in your preferred
              region.
           </td>
        </tr>
     </tbody></table>
  </div>
</div></blockquote>

&mdash; Amazon Web Services, Inc. (2018). [Option 1: Parameters for deploying MongoDB into a new VPC](https://docs.aws.amazon.com/quickstart/latest/mongodb/step2.html#new). *MongoDB on AWS MongoDB Quick Start: Step 2. Launch the Quick Start*.

Choose the EC2 Key you created above.

</li>
<li><blockquote><em>MongoDB Database Configuration:</em><table id="w151aac13c11b5b8c49">
  <tbody><tr>
    <th>Parameter label</th>
    <th>Parameter name</th>
    <th>Default</th>
    <th>Description</th>
  </tr>
  <tr>
     <td><b>MongoDB Admin Username</b></td>
     <td>MongoDBAdminUsername</td>
     <td>admin</td>
     <td>The user name for the MongoDB administrative account.</td>
  </tr>
  <tr>
     <td><b>MongoDB Admin Password</b></td>
     <td>MongoDBAdminPassword</td>
     <td><em class="replaceable"><code class="">Requires input</code></em></td>
     <td>Your MongoDB database password. You can enter an 8-32 character string consisting
        of the characters: [A-Za-z0-9_@-].
     </td>
  </tr>
</tbody></table>
</li>
<li><blockquote>
On the <b>Review</b> page, review and confirm the template settings. Under <b>Capabilities</b>, select the check box to acknowledge that the template will create IAM resources.
</blockquote>

&mdash; Amazon Web Services, Inc. (2018). [Option 1: Parameters for deploying MongoDB into a new VPC](https://docs.aws.amazon.com/quickstart/latest/mongodb/step2.html#new). *MongoDB on AWS MongoDB Quick Start: Step 2. Launch the Quick Start*.

<blockquote>
<label class="checkbox ng-scope" ng-repeat="capability in stack.capabilities.collection"> <input name="CAPABILITY_NAMED_IAM" ng-model="stack.capabilities.capabilitiesProvided[capability]" class="ng-valid ng-dirty ng-valid-parse ng-touched" type="checkbox"> <!-- ngIf: capability === capabilityIAM --> <!-- ngIf: capability === capabilityNamedIAM --><strong ng-if="capability === capabilityNamedIAM" class="ng-scope">I acknowledge that AWS CloudFormation might create IAM resources with custom names.</strong><!-- end ngIf: capability === capabilityNamedIAM --> <!-- ngIf: capability !== capabilityIAM && capability !== capabilityNamedIAM --> </label></blockquote>

&mdash; Amazon Web Services, Inc. (2018). Review. *AWS Cloud Formation: Create a New Stack*.

</li>
<li>
<blockquote>Choose <b>Create</b> to deploy the stack.</blockquote>

&mdash; Amazon Web Services, Inc. (2018). [Option 1: Parameters for deploying MongoDB into a new VPC](https://docs.aws.amazon.com/quickstart/latest/mongodb/step2.html#new). *MongoDB on AWS MongoDB Quick Start: Step 2. Launch the Quick Start*.


<button class="btn btn-primary" disabled>Create</button>
</li>
<li>
<blockquote>Monitor the status of the stack. When the status is <b>CREATE_COMPLETE</b>, as shown in Figure 6, the MongoDB cluster is ready.</blockquote>

&mdash; Amazon Web Services, Inc. (2018). [Option 1: Parameters for deploying MongoDB into a new VPC](https://docs.aws.amazon.com/quickstart/latest/mongodb/step2.html#new). *MongoDB on AWS MongoDB Quick Start: Step 2. Launch the Quick Start*.

</li>
</ol>
</ol>
