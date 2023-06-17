#!/usr/local/bin/python3

import datetime
import ipaddress

from kubernetes import client, config

START_IDX = 1
NUM_NAMESPACES = 1000
POLICIES_PER_NS = 3
NS_NAME_PREFIX = "perfpol-ns-"
POLICY_NAME_PREFIX = "para-hello-"
DEPLOYMENT_NAME_PREFIX = "hello-app-"
REPLICAS_PER_DEPLOYMENT = 10
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


def create_policies():
    netv1 = client.NetworkingV1Api()
    tasks = []
    for i in range(START_IDX, NUM_NAMESPACES+1):
        namespaceName = NS_NAME_PREFIX + str(i)
        deploymentName = DEPLOYMENT_NAME_PREFIX + str(i)
        for j in range(1, POLICIES_PER_NS+1):
            policyName = POLICY_NAME_PREFIX + str(j)
            task = create_policy(netv1, policyName, namespaceName, {"app": deploymentName})
            tasks.append(task)
    # wait for tasks to complete
    print("Waiting for policy create/ to be successful")
    for task in tasks:
        ret = task.get()
        print("create policy name", ret.metadata.name, "namespace", ret.metadata.namespace, task.successful())


def create_policy(netv1: client.NetworkingV1Api, name: str, namespace: str, podSelector: map):
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
    #return netv1.create_namespaced_network_policy(namespace, policy,  async_req=True)
    return netv1.patch_namespaced_network_policy(name, namespace, policy,  async_req=True)

def assign_pod_ips():
    # Dump list of pods with currently assigned ips so don't duplicate
    get_next_ip = ip_allocator()
    v1 = client.CoreV1Api()
    used_ips = set()
    pod_list = v1.list_pod_for_all_namespaces(watch=False)
    pod: client.V1Pod
    update_pod_list = []

    for pod in pod_list.items:
        pod_metadata: client.V1ObjectMeta
        pod_metadata = pod.metadata()
        try:
            pod_ip=pod_metadata.annotations()["vpc.amazonaws.com/pod-ips"]
            used_ips.add(pod_ip)
        except ValueError:
            if DEPLOYMENT_NAME_PREFIX in pod.metadata.name:
                print("pod needs IP assignment", pod.metadata.name)
                update_pod_list.append(pod)
            pass

    print("Initiating IP assignment for", len(update_pod_list), "pods")
    tasks = []
    for pod in update_pod_list:
        body = {
            "metadata": {
                "annotations": {
                    "vpc.amazonaws.com/pod-ips": get_next_ip(),
                }
            }
        }
        tasks.append(v1.patch_namespaced_pod(pod.metadata.name, pod.metadata.namespace, body, async_req=True))

    for task in tasks:
        ret = task.get()
        print("patched pod", ret.metadata.name, ret.metadata.namespace, task.successful())

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

def main():
    print("Test start", datetime.datetime.now())
    config.load_kube_config()
    #label_namespaces()
    #create_policies()
    assign_pod_ips()
    print("Test end", datetime.datetime.now())


if __name__ == '__main__':
    main()