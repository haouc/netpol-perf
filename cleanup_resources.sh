#! /bin/bash
#set -o errexit
#set -o nounset
#set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Cleaning up resources"
  for i in `seq 1 ${NUM_NAMESPACES}`; do
    nsName=${NS_NAME_PREFIX}${i}
    echo "Deleting namespace $nsName"
    k8s::delete_namespace $nsName
  done
}

main $@