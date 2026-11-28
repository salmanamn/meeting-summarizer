# The meeting summarizer as a Functions container (Project 7, D54). The base is Microsoft's Functions image for
# Python 3.13, pinned by digest: scripts/pin_base_image.py rewrites the FROM line. Built and checked by CI (the image
# job); not published, because PyAV's wheels bundle FFmpeg with GPL codecs (the same reason as Project 4 D61): the
# platform takes CI's artifact into its own registry (Project 7 D29).
FROM mcr.microsoft.com/azure-functions/python:4-python3.13@sha256:9ebf4f388230a0a7d6515ee4b5bdc4371484bf89eaf566c59ed80dd6f6671ff3

# The host listens on 8080 (the container runs as a user that can't bind 80) and logs to the console. The job reads
# the queue (D55): the Event Grid Blob trigger needs Event Grid to call into the container, which a private cluster
# doesn't offer.
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    ASPNETCORE_URLS=http://+:8080 \
    PORT=8080 \
    MEETING_TRIGGER=queue \
    MODELS_LOCK=/opt/meeting-models/models.lock.json

# Python 3.13 workers load an app's packages from .python_packages only (dependency isolation; anywhere else some
# packages make the worker exit with 139, azure-functions-python-worker issue 1797). The same requirements as the
# Flex package (D10, D37).
COPY src/requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --disable-pip-version-check --target /home/site/wwwroot/.python_packages/lib/site-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY src/ /home/site/wwwroot/
# The models Job's lock (D56): the committed one, so a pod downloads exactly the bytes the lock names.
COPY models.lock.json /opt/meeting-models/models.lock.json
# The fake LLM for a laptop cluster (stdlib Python): only the chart's lab profile starts it.
COPY scripts/fake_llm.py /opt/meeting-lab/

# A fixed non-root user (Pod Security "restricted" needs a numeric uid). It owns the directories the host writes
# to, not the code.
RUN groupadd --gid 10001 meeting \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /home --shell /usr/sbin/nologin meeting \
    && mkdir -p /local /tmp/metrics \
    && chown 10001:10001 /home /local /tmp/metrics
USER 10001:10001
EXPOSE 8080
LABEL org.opencontainers.image.source=https://github.com/salmanamn/meeting-summarizer \
    org.opencontainers.image.description="Meeting summarizer (Azure Functions, Python 3.13), for a cluster" \
    org.opencontainers.image.licenses=MIT