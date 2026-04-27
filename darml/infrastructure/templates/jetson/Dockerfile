FROM nvcr.io/nvidia/l4t-ml:r36.2.0-py3
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY inference.py model.tflite ./
CMD ["python3", "inference.py"]
