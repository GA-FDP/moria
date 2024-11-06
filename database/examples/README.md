### Usage

1. Create a test database using `database_utils/create_database 'test_db'`, assuming the MongoDB service is setup and running on your desired server.
2. Modify the `moria_path` variable in `examples.py`.
3. Run `example.py 0`, which will add two instruments and one diagnostic to the database.
4. Run `example.py 1`, to archive simulated data & images to the database. These correspond to the devices set up in `step 2`.
5. To perform three simulated queries on the previously archived data run `example.py 2`.
6. Feel free to modify and play around with different setups.
