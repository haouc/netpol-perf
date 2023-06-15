#! /bin/bash
set -o errexit
set -o nounset
set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Adding additional label to namespaces"
  namespaces=$(kubectl get namespaces -ojsonpath={.items..metadata.name})
  for ns in $namespaces; do
    kubectl label namespace $ns newlabel=value&
  done
}

main $@
