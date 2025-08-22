
set -e

sleep 4

echo -e "\n\n======================================================="
echo -e ">>>>>>>>>>>>>>>>git configuration<<<<<<<<<<<<<<<<<<<<<<"
echo -e "=======================================================\n\n"

sleep 4


echo -e ">>>>>>>>>>>>>>>>update<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\n"

sudo apt update && sudo apt upgrade -y && sudo apt-get update && sudo apt-get upgrade -y

sleep 4

echo -e "\n\n>>>>>>>>>>>>>>>installing dependencies<<<<<<<<<<<<<<<<<\n\n"

sudo apt install -y git gnupg2 openssh-client

sleep 4

echo -e "\n\n>>>>>>>>>>>>>>>Authorization youe own data<<<<<<<<<<<<<\n\n"

git config --global user.name "Babak Yousefian"
git config --global user.email "babakyousefian2000@gmail.com"

sleep 4

echo -e "\n\n>>>>>>>>>>>>>>depicts of configuration<<<<<<<<<<<<<<<<<\n\n"

git config --global --list

sleep 4

echo -e "\n\n>>>>>>>>>>>>>>create SSH key<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\n"

ssh-keygen -t ed25519 -C "babakyousefian2000@gmail.com"

sleep 4

echo -e "\n\n>>>>>>>>>>>>>check the agent of ssh key<<<<<<<<<<<<<<<<\n\n"

eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

cat ~/.ssh/id_ed25519.pub

echo -e "\n\n copy and paste the key in GitHub → Settings → SSH and GPG keys → New SSH key\n\n"

sleep 66

echo -e "\n\n>>>>>>>>>>>connection test<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n\n"

ssh -T git@github.com

sleep 4

