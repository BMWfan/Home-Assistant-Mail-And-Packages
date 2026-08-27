# Small dedicated image for the one-shot HA owner bootstrap, instead of
# apk-installing bash/curl/jq on every `docker compose up` via a bare
# alpine base -- this bakes the deps in once at build time so repeat
# starts don't pay the apk-add cost again.
FROM alpine:3.20
RUN apk add --no-cache bash curl jq
COPY bootstrap-owner.sh /bootstrap-owner.sh
ENTRYPOINT ["bash", "/bootstrap-owner.sh"]
