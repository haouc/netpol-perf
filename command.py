#!/usr/local/bin/python3

import datetime
import ipaddress
import time

from kubernetes import client, config
from typing import List

START_IDX = 1
NUM_NAMESPACES = 1000
POLICIES_PER_NS = 3
NS_NAME_PREFIX = "perfpol-ns-"
POLICY_NAME_PREFIX = "para-hello-"
DEPLOYMENT_NAME_PREFIX = "hello-app-"
REPLICAS_PER_DEPLOYMENT = 25
WAIT_UNTIL_DEPLOYMENT_READY = 0

class ResourceConfig:
    pass

def label_namespaces():
    v1=client.CoreV1Api()
    body = {
        "metadata": {
            "labels": {
                "newlabel": "value",
            }
        }
    }
    ns_list = v1.list_namespace(watch=False)
    async_tasks = []
    for ns in ns_list.items:
        print("Initiating label namespace: ", ns.metadata.name)
        task = v1.patch_namespace(ns.metadata.name, body, async_req=True)
        async_tasks.append(task)

    for task in async_tasks:
        print("Waiting for labeling to complete")
        resp=task.get()
        print("Labelled namespace", resp.metadata.name, task.successful())


def create_policies(netv1: client.NetworkingV1Api):
    tasks = []
    for i in range(START_IDX, NUM_NAMESPACES+1):
        namespaceName = NS_NAME_PREFIX + str(i)
        deploymentName = DEPLOYMENT_NAME_PREFIX + str(i)
        for j in range(1, POLICIES_PER_NS+1):
            policyName = POLICY_NAME_PREFIX + str(j)
            task = create_policy(netv1, policyName, namespaceName, {"app": deploymentName})
            tasks.append(task)
    # wait for tasks to complete
    print("Waiting for policy create to complete")
    for task in tasks:
        ret = task.get()
        print("create policy name", ret.metadata.name, "namespace", ret.metadata.namespace, task.successful())

def create_namespace(v1: client.CoreV1Api, name: str):
    namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=name,
            labels={
                "aname": name,
                "global": "select",
            }
        )
    )
    return v1.create_namespace(namespace, async_req=True)

def delete_namespace(v1: client.CoreV1Api, name: str):
    return v1.delete_namespace(name, async_req=True)

def create_deployment(appsv1: client.AppsV1Api, name: str, namespace: str, replicas: int):
    def getEnvList(num : int) -> List[client.V1EnvVar]:
        envList = []
        for i in range(num):
            envList.append(client.V1EnvVar(name="ENV_POD_GENERATE_KEY_INDEX_VALUE"+str(i), value="pod environment value " + str(i)))
        return envList

    pod_labels={
        'app':name,
        'ports':'multi',
        'allow':'ingress',
        'block':'egress',
    }
    for i in range(22):
        pod_labels['label_key_'+str(i)] = 'label-value-' + str(i)

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace
        ),
        spec=client.V1DeploymentSpec(
            strategy=client.V1DeploymentStrategy(
                type="RollingUpdate",
                rolling_update=client.V1RollingUpdateDeployment(
                    max_surge='100%',
                    max_unavailable='25%'
                ),
            ),
            replicas=replicas,
            selector=client.V1LabelSelector(match_labels={"app": name}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels=pod_labels
                ),
                spec=client.V1PodSpec(
                    node_selector={'allow-multi-deploy': 'enabled'},
                    containers=[
                        client.V1Container(
                            env=getEnvList(10),
                            name='multi',
                            image='public.ecr.aws/kishorj/hello-multi:v1',
                            ports=[
                                client.V1ContainerPort(
                                    name='http',
                                    container_port=80
                                ),
                                client.V1ContainerPort(
                                    name='https',
                                    container_port=443
                                )
                            ]
                        )
                    ]
                )
            )
        )
    )
    return appsv1.create_namespaced_deployment(namespace, deployment, async_req=True)


def build_policy(name: str, namespace: str, podSelector: map):
    policy = client.V1NetworkPolicy(
        api_version="networking.k8s.io/v1",
        kind="NetworkPolicy",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace
        ),
        spec=client.V1NetworkPolicySpec(
            pod_selector=podSelector,
            ingress=[client.V1NetworkPolicyIngressRule(
                _from=[
                    client.V1NetworkPolicyPeer(pod_selector=client.V1LabelSelector(match_labels={"allow": "ingress"})),
                ],
                ports=[
                    client.V1NetworkPolicyPort(port=443, protocol="TCP"),
                    client.V1NetworkPolicyPort(port=53, protocol="UDP"),
                    client.V1NetworkPolicyPort(port=80),
                ]
            )],
            egress=[client.V1NetworkPolicyEgressRule(
                to = [
                    client.V1NetworkPolicyPeer(pod_selector=client.V1LabelSelector(match_labels={"allow": "egress"}))
                ],
                ports=[
                    client.V1NetworkPolicyPort(port=443, protocol="TCP"),
                    client.V1NetworkPolicyPort(port=80),
                ]
            ), client.V1NetworkPolicyEgressRule(
                to = [
                    client.V1NetworkPolicyPeer(namespace_selector=client.V1LabelSelector(match_labels={"kubernetes.io/metadata.name": namespace}))
                ]
            )]
        )
    )
    return policy

def create_policy(netv1: client.NetworkingV1Api, name, namespace: str, podSelector: map):
    policy = build_policy(name, namespace, podSelector)
    return netv1.create_namespaced_network_policy(namespace, policy,  async_req=True)


def patch_policy(netv1: client.NetworkingV1Api, name: str, namespace: str, podSelector: map):
    policy = build_policy(name, namespace, podSelector)
    return netv1.patch_namespaced_network_policy(name, namespace, policy,  async_req=True)


def assign_pod_ips(v1: client.CoreV1Api):
    get_next_ip = ip_allocator()
    used_ips = set()
    update_pod_list = []
    # First, dump list of pods with currently assigned ips to prevent duplication
    # Use pagination to list all pods
    continue_token = None
    pods = []
    while True:
        pod_list_response = v1.list_pod_for_all_namespaces(watch=False, limit=2500, _continue=continue_token)
        pods.extend(pod_list_response.items)
        print("Got ", len(pod_list_response.items), "pods for the pod list")
        continue_token = pod_list_response.metadata._continue
        if not continue_token:
            break

    for pod in pods:
        pod_metadata: client.V1ObjectMeta
        pod_metadata = pod.metadata
        try:
            pod_ip=pod_metadata.annotations["vpc.amazonaws.com/pod-ips"]
            used_ips.add(pod_ip)
        except (KeyError, TypeError):
            if DEPLOYMENT_NAME_PREFIX in pod.metadata.name:
                print("pod needs IP assignment", pod.metadata.name)
                update_pod_list.append(pod)
            pass

    print("Initiating IP assignment for", len(update_pod_list), "pods")
    tasks = []
    for pod in update_pod_list:
        next_ip = get_next_ip()
        while next_ip in used_ips:
            next_ip = get_next_ip()
        body = {
            "metadata": {
                "annotations": {
                    "vpc.amazonaws.com/pod-ips": next_ip,
                }
            }
        }
        try:
            tasks.append(v1.patch_namespaced_pod(pod.metadata.name, pod.metadata.namespace, body, async_req=True))
        except Exception as e:
            print("unable to initiate pod patch", e)
            time.sleep(2)

    for task in tasks:
        try:
            ret = task.get()
            print("patched pod", ret.metadata.name, ret.metadata.namespace, task.successful())
        except Exception as e:
            print("Unable to get ip assignment status", e)
            time.sleep(2)

    print("Completed IP assignment for pods", len(update_pod_list), "pods")


def ip_allocator():
    start_ip="10.10.16.1"
    current_addr=ipaddress.IPv4Address(start_ip)
    def allocator_fn():
        nonlocal current_addr
        addr = str(ipaddress.ip_address(current_addr))
        current_addr += 1
        return addr
    return allocator_fn

def scale_deployment(appsv1: client.AppsV1Api, name: str, namespace: str, replicas: int):
    body = {
       "spec": {
           "replicas": replicas
        }
    }
    return appsv1.patch_namespaced_deployment_scale(name, namespace, body, async_req=True)

def create_resources():
    v1 = client.CoreV1Api()
    netv1 = client.NetworkingV1Api()
    appsv1=client.AppsV1Api()

    tasks = []
    for i in range(START_IDX, NUM_NAMESPACES+1):
        namespaceName = NS_NAME_PREFIX + str(i)
        print("Initiate create namespace", namespaceName)
        try:
            task = create_namespace(v1, namespaceName)
            tasks.append(('namespace', namespaceName, task))
        except Exception as e:
            print("Unable to initiate create namespace", e)
            time.sleep(2)

        try:
            deploymentName = DEPLOYMENT_NAME_PREFIX + str(i)
            print("Initiate create deployment", deploymentName)
            tasks.append(('deployment', "{}/{}".format(namespaceName, deploymentName),
                create_deployment(appsv1, deploymentName, namespaceName, REPLICAS_PER_DEPLOYMENT)))
        except Exception as e:
            print("Unable to initiate create deployment, sleeping 2s", e)
            time.sleep(2)

        for j in range(1, POLICIES_PER_NS+1):
            try:
                policyName = POLICY_NAME_PREFIX + str(j)
                task = create_policy(netv1, policyName, namespaceName, {"app": deploymentName})
                tasks.append(('policy', "{}/{}".format(namespaceName, policyName), task))
            except Exception as e:
                print("Unable to initiate create policy", e)
                time.sleep(2)

    # wait for tasks to complete
    print("Waiting for create tasks to complete")
    for resourceType, resourceName, task in tasks:
        try:
            task.get()
            print("create", resourceType, "id", resourceName, task.successful())
        except Exception as e:
            print("Failed to wait for create to complete", e)

    print("Assigining pod ips")
    #assign_pod_ips(v1)

def delete_resources():
    v1 = client.CoreV1Api()
    tasks = []
    for i in range(START_IDX, NUM_NAMESPACES+1):
        namespaceName = NS_NAME_PREFIX + str(i)
        print("Initiating namespace delete", namespaceName)
        tasks.append((namespaceName, delete_namespace(v1, namespaceName)))
    for ns, task in tasks:
        task.get()
        print('deleting namespace ', ns, 'status', task.successful())

def scale_and_assign_ips(v1: client.CoreV1Api, replicas: int):
    v1 = client.CoreV1Api()
    appsv1 = client.AppsV1Api()
    tasks = []
    for i in range(START_IDX, NUM_NAMESPACES+1):
        namespaceName = NS_NAME_PREFIX + str(i)
        deploymentName = DEPLOYMENT_NAME_PREFIX + str(i)
        print("Initiating scale deployment", namespaceName, deploymentName, "replicas", replicas)
        try:
            tasks.append(("{}/{}".format(namespaceName, deploymentName),
                scale_deployment(appsv1, deploymentName, namespaceName, replicas)))
        except Exception as e:
            print("Failed to initate deployment scale", e)
    for id, task in tasks:
        try:
            task.get()
            print('scale deployment', id, 'status', task.successful())
        except Exception as e:
            print("Failed to wait for deployment to be successful", e)
    #print("Assigning IPs")
    #assign_pod_ips(v1)

def main():
    print("Test start", datetime.datetime.now())
    config.load_kube_config()
    # operations
    # Create resources
    # create_resources()

    # Scale and assign IPs
    v1 = client.CoreV1Api()
    #scale_and_assign_ips(v1, 25)
    assign_pod_ips(v1)

    # Delete resources
    # delete_resources()
    print("Test end", datetime.datetime.now())


if __name__ == '__main__':
    main()
