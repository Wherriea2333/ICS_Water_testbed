# download redis
if [ -f "./redis-stable.tar.gz" ]; then
  echo "Redis already downloaded"
else
  echo "Downloading Redis"
  wget https://download.redis.io/redis-stable.tar.gz
fi
#  extract redis
if [ -d "./redis-stable" ]; then
  echo "Redis already extracted"
else
  echo "Extracting Redis"
  tar -xvzf redis-stable.tar.gz
fi
# install redis
echo  "Installing Redis"
cd redis-stable && make
sudo make install
cd ..
