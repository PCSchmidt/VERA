# Sandbox image for the TreeHFD loop (docs/04 T4). Build context: a checkout of
#   https://github.com/ThalesGroup/treehfd  at commit dd021526a9c97424334361d97cb88efe6f4e1b39
# placed in ./treehfd, then: docker build -t vera-sandbox-treehfd:dd02152 docker/sandbox-treehfd
FROM python:3.12-slim
COPY treehfd /opt/treehfd
RUN pip install --no-cache-dir /opt/treehfd && useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /work
