# Import plan creation scripts

The `make_plan.py` script in this directory turns a CSV list of servers to import into an import plan, that can then be executed.

### Usage:

```
pip3 install -r ../requirements.txt
python3 make_plan.py -s <source CSV file> -e < ID of the environment to import in> -o <output file name>
```

The csv file must have the following format:
```
server id, farm name, farm role alias, region, instance type, VPC id, subnet, role id, security groups (space separated), project id
```
Example line:
```
i-12345678,Pricing cluster,Elasticsearch,us-west-1,m3.medium,vpc-c442fba0,subnet-9c60f4ea,58832,sg-c1f92fa7 sg-123456,30c59dba-fc9b-4d0f-83ec-4b5043b12f72
```

Remarks on the different fields:
 - The role ID (58832 in the example) is the ID of a Scalr Role that is linked to System Images to allow the import. The OS of the Role must correspond to the OS of the servers being imported. Images must be added to the Role for all the EC2 regions where servers will be imported from.
 - The region, instance type, VPC ID, Role ID, list of security group IDs must be the same for all the servers in a given farm Role
 - The subnets do not need to be the same for all the servers in one farm role (there is one per availability zone in AWS, all those that are used will be added to the farm role).
 - The Project ID must be the same for all the servers in a Farm
 - The project ID is the ID of the Scalr Project into which the cost incurred by the Farm will be recorded. It can be retrieved using our API: https://api-explorer.scalr.com/user/projects/get.html



The script will create two plans, one to create the farms and farm roles, and one to import the servers.
