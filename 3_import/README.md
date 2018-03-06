# Import plan execution

The `bulk_import.py` script in this directory executes the import plans created in the previous step.

The script saves its progress after each successful step - so it is safe to run it multiple times or to relaunch it if it is interrupted. To clear the saved state, for instance if you made changes to Scalr that require a new run (creating or deleting target farms and farm roles), remove the `.status` file that is created next to the import plan.

### Order of events
1. Run the setup
2. Run the import

### Usage

```
python3 bulk_import.py -u <scalr URL> -k <API Key> -s <API Key secret> -p <Plan file to execute>
```




