# Import plan creation scripts

The `make_plan.py` script in this directory turns a CSV list of servers to import into an import plan, that can then be executed.

### Usage:

```
pip3 install -r ../requirements.txt
python3 make_plan.py --help
python3 make_plan.py -P ec2 -s <source CSV file> -e < ID of the environment to import in> -o <output file prefix>
```

*** If the project name is used instead of the project ID, add a -p at the end of the command:
```
python3 make_plan.py -s <source CSV file> -e < ID of the environment to import in> -o <output file prefix> -p
```

The script will create two plans, one to create the farms and farm roles, and one to import the servers.


### EC2 Imports

The csv file must have the following format:
```
server id, farm name, farm role alias, region, instance type, VPC id, subnet, role id, security groups (space separated), project id or name
```
Example line:
```
i-12345678,Pricing cluster,Elasticsearch,us-west-1,m3.medium,vpc-c442fba0,subnet-9c60f4ea,58832,sg-c1f92fa7 sg-123456,30c59dba-fc9b-4d0f-83ec-4b5043b12f72
```

Remarks on the different fields:
 - The role ID (58832 in the example) is the ID of a Scalr Role that is linked to System Images to allow the import. The OS of the Role must correspond to the OS of the servers being imported.
 - The subnets do not need to be the same for all the servers in one farm role (there is one per availability zone in AWS, all those that are used will be added to the farm role).
 - The Project ID must be the same for all the servers in a Farm
 - The project ID is the ID of the Scalr Project into which the cost incurred by the Farm will be recorded. It can be retrieved using our API: https://api-explorer.scalr.com/user/projects/get.html . When using the `-p` flag, project names can be passed directly in this field.

### VMware imports
The csv file must have the following format:
```
vm id, farm name, farm role alias, datacenter, instance type, network id, role id, compute resource id, host id, project id or name, folder id, resource group id, datastore id
```
Example line:
```
vm-1373,FarmName,Farm-role-name,datacenter-21,0f52797dd8ba,network-30,96554,domain-s26,host-28,IT Lab,group-v22,resgroup-27,datastore-29
```

Remarks on the different fields:
 - The role ID (58832 in the example) is the ID of a Scalr Role that is linked to System Images to allow the import. The OS of the Role must correspond to the OS of the servers being imported.
 - The instance type field corresponds to the Scalr ID for a VMware instance type. This ID is used when creating Farm Roles for the import, and can be retrieved from our API: https://api-explorer.scalr.com/user/clouds/cloud-locations/instance-types/get.html
 - The Project ID must be the same for all the servers in a Farm
 - The project ID is the ID of the Scalr Project into which the cost incurred by the Farm will be recorded. It can be retrieved using our API: https://api-explorer.scalr.com/user/projects/get.html . When using the `-p` flag, project names can be passed directly in this field.
