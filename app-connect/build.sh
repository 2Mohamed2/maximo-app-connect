#!/bin/bash
# Build MaximoFieldErp.bar with ibmint inside the App Connect Enterprise image (no Toolkit needed).
# ACEBUILD: a work folder podman can mount (on Windows Git Bash, a C:/... style path).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; W="${ACEBUILD:-/tmp/acebuild}"
python "$HERE/gen_flows.py" >/dev/null
rm -rf "$W/MaximoFieldErp" && mkdir -p "$W" && cp -r "$HERE/MaximoFieldErp" "$W/"
MSYS_NO_PATHCONV=1 podman run --rm --entrypoint bash -v "$W:/work" cp.icr.io/cp/appc/ace-server-prod:13.0.7.2-r1-20260524-190429 -c \
 'source /opt/ibm/ace-13/server/bin/mqsiprofile >/dev/null 2>&1; cp -r /work/MaximoFieldErp /tmp/ && ibmint package --input-path /tmp --project MaximoFieldErp --output-bar-file /work/MaximoFieldErp.bar | tail -1'
cp "$W/MaximoFieldErp.bar" "$HERE/"
