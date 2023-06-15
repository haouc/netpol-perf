#! /bin/bash
set -o errexit
set -o nounset
set -o pipefail

. ./resource-config.sh
. ./common-utils.sh
. ./k8s-utils.sh

# Use start IP address 10.10.16.1
current_address=$((0x0a0a1001))

main() {
  util::echo_time "Assigning pod IP addresses"
  for i in `seq ${START_IDX} ${NUM_NAMESPACES}`; do
    nsName=${NS_NAME_PREFIX}${i}
    echo "querying deployments in the namespace $nsName"

    deployments=$(kubectl get deploy -n $nsName -ojsonpath={.items..metadata.name})
    for deployment in $deployments; do
      util::echo_time "processing deployment $deployment"
      pods=$(kubectl get pods -n $nsName -l app=$deployment -ojsonpath={.items..metadata.name})
      for pod in $pods; do
        ip_address=$(python3 -c "import ipaddress; print(str(ipaddress.ip_address($current_address)))")
        util::echo_time "annotating pod $pod with ip address $ip_address"
        kubectl annotate --overwrite -n $nsName pod $pod vpc.amazonaws.com/pod-ips=$ip_address &
        current_address=$((current_address+1))
      done
    done
  done
}

main $@
