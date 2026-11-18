# Python. SDK=1 installs the antithesis package and starts the worker with
# `python -m antithesis`; alerts has neither, so it reports no coverage.
FROM python:3-slim-trixie
ARG SDK=1
COPY worker.py pyproject.toml /app/
RUN mkdir -p /opt/antithesis && ln -s /app /opt/antithesis/catalog \
 && if [ "$SDK" = 1 ]; then pip install --no-cache-dir antithesis \
      && printf '#!/bin/sh\nexec python -m antithesis /app/worker.py\n' > /usr/local/bin/python-service; \
    else printf '#!/bin/sh\nexec python /app/worker.py\n' > /usr/local/bin/python-service; fi \
 && chmod 755 /usr/local/bin/python-service
CMD ["/usr/local/bin/python-service"]
