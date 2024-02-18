# download OpenPLC
if [ -d "./OpenPLC_v3" ]; then
    echo "OpenPLC_v3 already clone" >> openplc_install.log
else
  echo "Clone OpenPLC_v3" >> openplc_install.log
  git clone https://github.com/thiagoralves/OpenPLC_v3.git
fi
# install OpenPLC_v3
echo "Install OpenPLC_v3" >> openplc_install.log

(
cd OpenPLC_v3 || exit
./install.sh linux
# start openplc
echo "Start OpenPLC_v3" >> openplc_install.log
./start_openplc.sh &
)

