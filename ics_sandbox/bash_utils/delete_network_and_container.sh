#!/bin/bash

# check if running as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi
# stop container
for i in {1..6}
do
  docker container stop plc"$i"
done
# remove container
for i in {1..6}
do
  docker container rm plc"$i"
done
# remove network
sudo docker rm swat