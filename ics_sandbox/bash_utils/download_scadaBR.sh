# download scadaBR
if [ -d "./scadabr" ]; then
    echo "scadaBR already clone" >> openplc_install.log
else
  echo "Clone scadaBR" >> openplc_install.log
  git clone https://github.com/Wherriea2333/scadabr.git
fi
