## General Instructions

### Notes
This directory contains utilities for the MORIA framework: 
####
**IMPORTANT** 
- these commands may require root privileges
- modify the `LOG_FILE` path in the scripts 
- these commands requires the `mongod` service to be running
  - **start**: `sudo service mongod start` | **stop**: `sudo service mongod stop` 

##
### Command Instructions
./create_database <database_name>
**Example:** 
`./create_database moria`
####
./backup_database <database_name> <backup_directory>
**Example:** `./backup_database moria /data/mongo_data_backup/prod/`
####
./restore_database <database_name> <saved_backup_directory>
**Example:** `./restore_database moria /data/mongo_data_backup/prod/moria_2024-07-26_14:28:49`


## 
### Optional Considerations
- Create a daily backup cron job
   - `/etc/crontab`
   - `00 01 * * 1-5 root /usr/local/bin/backup_database moria /data/mongo_data_backup/prod`
