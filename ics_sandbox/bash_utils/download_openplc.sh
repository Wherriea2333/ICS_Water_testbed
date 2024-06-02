# download OpenPLC
if [ -d "./OpenPLC_v3" ]; then
    echo "OpenPLC_v3 already clone" >> openplc_install.log
else
  echo "Clone OpenPLC_v3" >> openplc_install.log
  git clone https://github.com/Wherriea2333/OpenPLC_v3_customized.git
fi

