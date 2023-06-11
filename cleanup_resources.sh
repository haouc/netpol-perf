#! /bin/bash
set -o errexit
set -o nounset
set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Cleaning up resources"
  for i in `seq ${START_IDX} ${NUM_NAMESPACES}`; do
    nsName=${NS_NAME_PREFIX}${i}

    for j in `seq ${START_IDX} ${POLICIES_PER_NS}`; do
      policyName=para-hello-${j}
      k8s::delete_policy $policyName $nsName || true
    done

    deploymentName=hello-app-${i}
    k8s::delete_deployment $deploymentName $nsName || true

    k8s::delete_namespace $nsName || true
  done
}

main $@