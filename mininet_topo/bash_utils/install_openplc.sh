# download OpenPLC
if [ -d "./OpenPLC_v3" ]; then
    echo "OpenPLC_v3 already clone"
else
  echo "Clone OpenPLC_v3"
  git clone https://github.com/thiagoralves/OpenPLC_v3.git
fi
# install OpenPLC_v3
echo "Install OpenPLC_v3"
cd OpenPLC_v3 || exit 2
./install.sh linux
# start openplc
echo "Start OpenPLC_v3"
./start_openplc.sh &
cd ..
