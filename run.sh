#!/bin/bash
set -e

sleep 4

# free any old processes (avoids "Address already in use")
sudo fuser -k 8000/tcp || true
sudo fuser -k 5500/tcp || true

sleep 2


echo -e "\n\n=========================================="
echo -e "wellcome to my own bash scripts...!!!"
echo -e "==========================================\n\n"

sleep 4

GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting FastAPI backend on port 8000...${NC}"

uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
PID1=$!

sleep 2

echo -e "${GREEN}Starting static HTML server on port 5500...${NC}"

python3.13 -m http.server 5500 &
PID2=$!

echo -e "${GREEN}Project running!${NC}"
echo "Backend:   http://127.0.0.1:8000"
echo "Frontend:  http://127.0.0.1:5500/index.html"

sleep 4

echo -e "\n\n"
read -p "Press [Enter] to stop servers..."
echo -e "\n\n"

sleep 4

echo -e "\n\n==========================================="
echo -e "the server has been stopped...!!!"
echo -e "===========================================\n\n"

kill $PID1 $PID2

sleep 4

echo -e "\n\nthe main proccess stop within exit code 0\n\n"
echo -e "@Author by: Babak yousefian"
sleep 4

