#!/bin/bash

if [ -z "$1" ]; then
    echo "Loi: Ban chua nhap ngay thang"
    exit 1
fi 

INPUT_DATE="$1"

DOW=$(date -d "$INPUT_DATE" +%u)

OFFSET=$(( (DOW+3)%7 ))

DATE=$(date -d "$INPUT_DATE - $OFFSET days" +%Y-%m-%d)

echo "================================"
echo "Ngay ban truyen vao : $INPUT_DATE"
echo "Thu 5 gan nhat la   : $DATE"
echo "Dang dong bo toan bo thu muc data len S3....."
echo "================================"

# Dong bo toan bo thu muc data len S3
aws s3 cp /opt/airflow/data/ s3://spotify-stream-bucket/"$DATE"/ --recursive

if [ $? -eq 0 ]; then
    echo "==> Upload tat ca cac file thanh cong!!"
    echo "Dang xoa cac file o local de giai phong dung luong..."
    
    # Xoa cac file nhung van giu lai cau truc thu muc (nhu artist, audio_feature, top_track, track_info)
    find /opt/airflow/data/ -type f -delete
    
    if [ $? -eq 0 ]; then
        echo "==> Xoa file thanh cong!!"
    else
        echo "==> Xoa file that bai"
    fi
else
    echo "==> Upload file that bai. Khong thuc hien xoa file local de an toan."
    exit 1
fi
