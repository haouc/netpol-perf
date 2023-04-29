#! /bin/bash
#set -o errexit
#set -o nounset
#set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Creating resources"
  for i in `seq 1 ${NUM_NAMESPACES}`; do
    nsName=${NS_NAME_PREFIX}${i}
    echo "Creating namespace $nsName"
    k8s::create_namespace $nsName
  done
}

main $@
