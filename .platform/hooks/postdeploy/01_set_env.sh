#!/bin/bash

#Create a copy of the environment variable file.
cp /opt/elasticbeanstalk/deployment/env /opt/elasticbeanstalk/deployment/custom_env_var

#Set permissions to the custom_env_var file so this file can be accessed by any user on the instance. You can restrict permissions based on your requirements.
chmod 644 /opt/elasticbeanstalk/deployment/custom_env_var

#Remove duplicate files upon deployment.
rm -f /opt/elasticbeanstalk/deployment/*.bak

# Add the following code to the 'ec2-user' bash profile to avoid manually sourcing the file on the instance.
source_cmd="source <(sed -E -n 's/[^#]+/export &/ p' /opt/elasticbeanstalk/deployment/custom_env_var)"
bash_profile_path=/home/ec2-user/.bash_profile
grep -qxF -- "$source_cmd" "$bash_profile_path" || echo $source_cmd >> $bash_profile_path
