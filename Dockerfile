FROM python:3.12.3-slim

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /code

# Configure pip to use mirrors and increase timeout
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.timeout 1000 \
    && pip config set global.retries 10

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src

# Set proper permissions
RUN chown -R appuser:appuser /code

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
