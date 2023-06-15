#! /bin/bash
set -o errexit
set -o nounset
set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Adding additional label to namespaces"
  ns=$(kubectl get namespaces -ojsonpath)
}

main $@
