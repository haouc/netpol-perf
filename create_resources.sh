#! /bin/bash
set -o errexit
set -o nounset
set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

main() {
  util::echo_time "Creating resources"
  for i in `seq 1 ${NUM_NAMESPACES}`; do
    nsName=${NS_NAME_PREFIX}${i}
    echo "Creating namespace $nsName"
    k8s::create_namespace $nsName

    deploymentName=hello-app-${i}
    k8s::create_deployment $deploymentName $REPLICAS_PER_DEPLOYMENT $nsName
    if [ $WAIT_UNTIL_DEPLOYMENT_READY -eq 1 ]; then
      k8s::wait_until_deployment_ready $deploymentName $nsName
    fi

    for j in `seq 1 ${POLICIES_PER_NS}`; do
      policyName=para-hello-${i}
      k8s::create_policy $policyName $nsName "app: $deploymentName"
    done
  done
}

main $@
