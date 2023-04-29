#!/bin/bash
#set -o errexit
#set -o nounset
#set -o pipefail

lbName=""
lbArn=""
tgtGrpArn=""
tgHealth=""

util::echo_time() {
    date +"%D %T $*"
}

k8s::create_deployment() {
NS=""
if [ ! -z $3 ]; then
	NS="-n $3"
fi
cat <<EOF | kubectl apply $NS -f -
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


k8s::wait_until_deployment_ready() {
	NS=""
	if [ ! -z $2 ]; then
		NS="-n $2"
	fi
	util::echo_time "Checking if deployment $1 is ready"
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
  kubectl delete deployment $1
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
  kubectl create namespace $namespace
  kubectl label namespace $namespace global=select
  kubectl label namespace $namespace aname=$namespace
}

k8s::delete_namespace() {
  util::echo_time "Deleting namespace $1"
  if [ -z $1 ]; then
    util::echo_time "cowardly refusing to delete empty namespace"
    return 1
  fi
  kubectl delete namespace $1
}
