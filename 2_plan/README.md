# Import plan creation scripts

The `make_plan.py` script in this directory turns a CSV list of servers to import into an import plan, that can then be executed.

### Usage:

```
pip3 install -r ../requirements.txt
python3 make_plan.py -s <source CSV file> --environment < ID of the environment to import in> -o <output file name>
```

The csv file must have the following format:
```
cloud server ID,Target farm name, Target farm role name
