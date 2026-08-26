FROM python:3.12-slim
WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN pip install --no-cache-dir -e "."
COPY docker/backend-entrypoint.sh ./docker/backend-entrypoint.sh
RUN chmod +x ./docker/backend-entrypoint.sh
EXPOSE 8000
CMD ["./docker/backend-entrypoint.sh"]
