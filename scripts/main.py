#!/usr/bin/env python
from constructs import Construct
from cdk8s import App, Chart

from imports import k8s
from typing import List


class MyChart(Chart):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # define resources here
        deployment_labels = {
            "app" : "perf-1",
            "ports" : "multi"
        }
        # Add generate 128 additional labels for pod spec
        pod_labels = {}
        for i in range(0, 128):
            pod_labels["label-key-"+str(i)]="label-value-"+str(i)

        pod_labels.update(deployment_labels)

        k8s.KubeDeployment(self, 'deployment',
            metadata=k8s.ObjectMeta(name="perf-deploy-1"),
            spec=k8s.DeploymentSpec(
                replicas=1,
                selector=k8s.LabelSelector(match_labels=deployment_labels),
                template=k8s.PodTemplateSpec(
                    metadata=k8s.ObjectMeta(labels=pod_labels),
                    spec=k8s.PodSpec(
                        containers=self.getContainerSpecs(30),
                        node_selector={"allow-multi-deploy": "enabled"}
                    )
                )
            )
        )

    def getEnvList(self, num : int) -> List[k8s.EnvVar]:
        envList = []
        for i in range(num):
            envList.append(k8s.EnvVar(name="ENV_POD_GENERATE_KEY_INDEX_VALUE"+str(i), value="pod environment value " + str(i)))
        return envList

    def getContainerSpecs(self, num: int) -> List[k8s.Container]:
        containerList = []
        containerList.append(
            k8s.Container(
                env=[k8s.EnvVar(name="ENV_HELLO_MULTI", value="type-multi")],
                name = "multi",
                image = "kishorj/hello-multi:v1",
                ports = [k8s.ContainerPort(container_port=8080, name="http")]
            )
        )
        for i in range(num):
            containerList.append(k8s.Container(
                    env=self.getEnvList(100),
                    name="pause" + str(i),
                    image="public.ecr.aws/eks-distro/kubernetes/pause:3.9"
                )
            )

        return containerList



app = App()
MyChart(app, "scripts")

app.synth()