FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-policy-api.txt /app/requirements-policy-api.txt
RUN pip install --no-cache-dir -r requirements-policy-api.txt
COPY policy_api /app/policy_api
EXPOSE 8000
CMD ["uvicorn", "policy_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
