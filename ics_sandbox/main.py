import subprocess

SUDO = "sudo"
BASH_UTILS = "bash_utils/"
OPENPLC_BASH = "download_openplc.sh"
DELETE_CONTAINER = "delete_network_and_container.sh"
CREATE_CONTAINER = "create_docker_network.sh"


def remove_network():
    subprocess.run([SUDO, BASH_UTILS + DELETE_CONTAINER], shell=True)


def create_network():
    subprocess.run([SUDO, BASH_UTILS + CREATE_CONTAINER], shell=True)


def download_open_plc():
    subprocess.run(["sudo", OPENPLC_BASH], shell=True)


if __name__ == '__main__':
    download_open_plc()
    create_network()
