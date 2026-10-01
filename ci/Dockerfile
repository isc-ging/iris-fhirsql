# CI image: IRIS for Health community (ZPM preinstalled) + fhir-server package.
# Separate from ../iris/Dockerfile, which builds the dev image.
FROM intersystemsdc/irishealth-community:latest

COPY --chown=irisowner:irisowner init.script /home/irisowner/init.script

# `iris session` exits 0 even when the script fails, so fail the build if the output has errors.
RUN iris start IRIS \
    && iris session IRIS -U %SYS < /home/irisowner/init.script | tee /tmp/init.log \
    && ! grep -E "ERROR!|INIT FAILED" /tmp/init.log \
    && iris stop IRIS quietly

# The base image's entrypoint runs a first-start init (create USER namespace, via embedded Python
# dbapi.connect) that crashes IRIS on intersystemsdc/irishealth-community 2026.1 build 235
# ("Cannot call an iris.package wrapper ... dbapi.connect"). The entrypoint skips that init when
# iris.init exists. Kept as its own layer so the slow fhir-server layer above stays cached.
RUN date > /usr/irissys/iris.init
