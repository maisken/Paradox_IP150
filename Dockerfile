ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Copy data for add-on
COPY run.sh /

RUN apk add --no-cache python3

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]