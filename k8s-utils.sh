#!/bin/bash
#set -o errexit
#set -o nounset
#set -o pipefail

lbName=""
lbArn=""
tgtGrpArn=""
tgHealth=""

k8s::create_policy() {
  policyName=""
  nsArg=""
  podSelector="app: hello"
  if [ ! -z $1 ]; then
    policyName=$1
  else
    util::echo_time "refusing to create policy with empty name"
    return 1
  fi
  if [ ! -z $2 ]; then
    nsArg="-n $2"
  fi
  if [ ! -z "$3" ]; then
    podSelector=$3
  fi
  util::echo_time "Creating policy $policyName, $nsArg, selector $podSelector"
  cat <<EOF | kubectl apply $nsArg $KUBECTL_DRY_RUN_FLAG -v=2 -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: $policyName
spec:
  podSelector:
    matchLabels:
      $podSelector
  ingress:
  - from:
    - podSelector:
        matchLabels:
          allow: ingress
    ports:
    - port: 443
      protocol: TCP
    - port: 53
      protocol: UDP
    - port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          allow: egress
    ports:
    - port: 443
      protocol: TCP
    - port: 53
      protocol: UDP
    - port: 80
EOF
}

k8s::create_deployment() {
NS=""
if [ ! -z $3 ]; then
	NS="-n $3"
fi
util::echo_time "Creating deployment $1 $NS, numReplicas $2"
cat <<EOF | kubectl apply $NS $KUBECTL_DRY_RUN_FLAG -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $1
spec:
  strategy:
    rollingUpdate:
      maxSurge: 100%
      maxUnavailable: 25%
    type: RollingUpdate
  replicas: $2
  selector:
    matchLabels:
      app: $1
  template:
    metadata:
      labels:
        app: $1
        ports: multi
        allow: ingress
        block: egress
    spec:
      containers:
        - name: multi
          imagePullPolicy: Always
          image: "kishorj/hello-multi:v1"
          ports:
            - name: http
              containerPort: 80
EOF
}

k8s::delete_policy() {
  policyName=""
  nsArg=""
  if [ ! -z $1 ]; then
    policyName=$1
  else
    echo_time "refusing to delete policy without a name"
    return 1
  fi
  if [ ! -z $2 ]; then
    nsArg="-n $2"
  fi

  util::echo_time "Deleting policy $policyName, $nsArg"
  kubectl delete netpol $policyName $nsArg $KUBECTL_DRY_RUN_FLAG
}

k8s::wait_until_deployment_ready() {
	NS=""
	if [ ! -z $2 ]; then
		NS="-n $2"
	fi
	util::echo_time "Checking if deployment $1 $NS is ready"
	for i in $(seq 1 60); do
		desiredReplicas=$(kubectl get deployments.apps $1 $NS -ojsonpath="{.spec.replicas}")
		availableReplicas=$(kubectl get deployments.apps $1 $NS -ojsonpath="{.status.availableReplicas}")
		if [[ ! -z $desiredReplicas && ! -z $availableReplicas && "$desiredReplicas" -eq "$availableReplicas" ]]; then
			break
		fi
		echo -n "."
		sleep 2
	done
	util::echo_time "Deployment $1 $NS replicas desired=$desiredReplicas available=$availableReplicas"
}


k8s::delete_deployment() {
  deploymentName=""
  nsArg=""
  if [ ! -z $1 ]; then
    deploymentName=$1
  else
    echo_time "unable to delete a deployment without a name"
  fi
  if [ ! -z $2 ]; then
    nsArg="-n $2"
  fi
	util::echo_time "deleting deployment $deploymentName $nsArg"
  kubectl delete deployment $deploymentName $nsArg $KUBECTL_DRY_RUN_FLAG
}

k8s::create_namespace() {
  namespace=""
	if [ ! -z $1 ]; then
	  namespace="$1"
	fi
  if [ "$namespace" == "" ]; then
    util::echo_time "Refusing to create empty namespace"
    return 1
  fi
  util::echo_time "Creating namespace $namespace"
  kubectl create namespace $namespace $KUBECTL_DRY_RUN_FLAG
  kubectl label namespace $namespace global=select $KUBECTL_DRY_RUN_FLAG
  kubectl label namespace $namespace aname=$namespace $KUBECTL_DRY_RUN_FLAG
}

k8s::delete_namespace() {
  util::echo_time "Deleting namespace $1"
  if [ -z $1 ]; then
    util::echo_time "cowardly refusing to delete empty namespace"
    return 1
  fi
  kubectl delete namespace $1 $KUBECTL_DRY_RUN_FLAG
}
