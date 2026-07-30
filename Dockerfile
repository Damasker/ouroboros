FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY docs ./docs
COPY tests ./tests
COPY Makefile ./

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir -e ".[dev]"

RUN python -c "from ouroboros.geometry import default_loop_geometry; default_loop_geometry().save('geometry/loop_geometry.json')"

CMD ["make", "test"]
