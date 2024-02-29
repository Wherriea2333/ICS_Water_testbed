#!/bin/bash

# check if running as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

# stop container
for i in {11..16}
do
  sudo docker ps | grep plc"$i":oplcv3 | awk '{ print $1 }' | xargs docker stop
done

# stop physical simulation
sudo docker ps | grep sim:sim | awk '{ print $1 }' | xargs docker stop

# remove container
for i in {11..16}
do
  sudo docker image rm plc"$i":oplcv3 --force
done
# remove physical simulation container
sudo docker image rm sim:sim --force

# remove network
sudo docker network rm swat