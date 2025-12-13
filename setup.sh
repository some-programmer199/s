sudo apt update && sudo apt install tinyproxy -y
sudo sed -i 's/^Port .*/Port 8000/' /etc/tinyproxy/tinyproxy.conf
sudo sed -i 's/^#*Listen .*/Listen 0.0.0.0/' /etc/tinyproxy/tinyproxy.conf
sudo systemctl restart tinyproxy
sudo systemctl enable tinyproxy
