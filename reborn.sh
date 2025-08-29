echo +e

echo "\n\n======================================="
echo "	babak yousefian"
echo "=======================================\n\n"

sleep 4

echo "\n\n======================================="
echo "	updating and upgrading"
echo "=======================================\n\n"

sleep 4

sudo apt update && sudo apt upgrade -y && sudo apt-get update && sudo apt-get upgrade -y

sleep 4


echo "\n\n======================================="
echo "start and enable the nginx server....!!!!"
echo "=======================================\n\n"

sleep 4

sudo systemctl enable nginx
sleep 3
sudo systemctl start nginx
sleep 3
sudo nginx -t

sleep 4


echo "\n\n======================================"
echo "rebuild and start docker....!!!!"
echo "======================================\n\n"

sleep 4

sudo docker compose down
sleep 3
sudo docker compose build --no-cache
sleep 3
sudo docker compose up -d --build

sleep 4


echo "\n\n======================================"
echo "	checker....!!!!"
echo "======================================\n\n"

sleep 4

sudo docker compose ps -a
sleep 3
sudo docker compose images
sudo docker images
sudo docker network ls

sleep 4

echo "\n\n======================================"
echo "	finished....!!!!"
echo "======================================\n\n"

sleep 1

echo "\n\n======================================"
echo "	@Author = babak yousefian"
echo "======================================\n\n"

sleep 4

echo "finished the process at exit code 1"

sleep 1
