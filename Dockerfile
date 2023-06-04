# Use the official Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the container
COPY . .

# Expose a port (replace 5000 with the appropriate port if needed)
EXPOSE 5000

# Set the entry point command to run the Flask app
CMD ["python", "app.py"]
