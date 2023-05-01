#! /bin/bash
set -o errexit
set -o nounset
set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Cleaning up resources"
  for i in `seq 1 ${NUM_NAMESPACES}`; do
    nsName=${NS_NAME_PREFIX}${i}

    for j in `seq 1 ${POLICIES_PER_NS}`; do
      policyName=para-hello-${i}
      k8s::delete_policy $policyName $nsName
    done

    deploymentName=hello-app-${i}
    k8s::delete_deployment $deploymentName $nsName

    k8s::delete_namespace $nsName
  done
}

main $@