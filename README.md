# simple-game-server-eks

This is an example of a dedicated game-server deployment in EKS using Spot Amazon EC2 Instances. The goal is to provide a robust and straightforward game-server deployment pattern on EKS. 

We use Minecraft as the example deployed based on [minecraft helm chart](https://hub.docker.com/r/itzg/minecraft-server/) with a slight modification in the deployment mechanism.

The proposal herein deploys a dedicated game server as a k8s pod with `hostnetwork:true` option. Each k8s node (EC2 Instance) deployed with a public hostname, and high port range is opened for client connectivity. Upon a game-server scheduling (pod scheduling), two high ports are allocated for the game server. The clients will connect the game-server using the public hostname and port assigned. [start.py](https://github.com/yahavb/simple-game-server-eks/blob/master/minecraft-server-image/start.py) act the game-server wrapper script for the original build. It uses a lazy-approach to generate the required set of dynamic high ports and passes it game-server as an environment variable upon the game-server init phase.  Initially, `socket.AF_INET` socket is started and bound to port `0`. The OS will allocate a socket on a high port. We will capture the port and release the socket right before we the server starts. There is a chance for a raise condition when multiple game-server will attempt to start on the same instance. That will resolve automatically by a continuous `CrashLoopBackOff`.  

``` python
def get_rand_port():
    # Attempting to get random port
    try:
      s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.bind(('',0))
    except socket.error as msg:
      print 'bind failed. Error is '+str(msg[0])+' Msg '+msg[1]
    print 'socket bind complete '
    port=s.getsockname()[1]
    s.close()
       return port
```


The proposed spec uses a [Deployment](https://github.com/yahavb/simple-game-server-eks/blob/master/specs/minecraft-gs-r1-12-deploy.yaml) k8s resource type that uses standard  `containers` environment variables defining the game-server init parameters. 

We also used SQS as a mechanism to mediate between the game-server and external system that maintain the game-server fleet transient state. Any such method can read the messages published on that queue and take action. To enable SQS access on EKS, simply update your worker nodes IAM role by adding an inline policy with the proper `region`, `account-id`, and `queuename` defined in [start.py](https://github.com/yahavb/simple-game-server-eks/blob/master/minecraft-server-image/start.py).

``` yaml
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:sqs:region:account-id:queuename"
        }
    ]
}
```

The EKS Bootstrap.sh script is packaged into the EKS Optimized AMI that we are using, and only requires a single input: the EKS Cluster name. The bootstrap script supports setting any kubelet-extra-args at runtime. You will need to configure node-labels so that kubernetes knows what type of nodes we have provisioned. Set the lifecycle for the nodes as `ondemand` or `spot`. Check out The Setup Process below for more information as well as [Improvements for Amazon EKS Worker Node Provisioning](https://aws.amazon.com/blogs/opensource/improvements-eks-worker-node-provisioning/).


## The Setup Process
* Create an EKS cluster using the [Getting Started with Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html) guide. The guestbook step is recommended for sanity test but not crucial to this scenario. 
* If an AWS Spot Instances is being used, apply [Step 3: Launch and Configure Amazon EKS Worker Nodes](https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html) from the guide but with Spot ASG. 
* One can use MixedInstancesPolicy where we allow EKS to opportunistically allocate compatibale spot instances for cost optimization.
For that, one should use the cloud formation template with the following parameters:

In our case, the Minecraft gameserver or any other gameserver exposed to the player thru ephemeral port allocated by [start.py](https://github.com/yahavb/simple-game-server-eks/blob/master/minecraft-server-image/start.py). Hence `ExistingNodeSecurityGroups` should be populated with the security group that allows the network access.  

check the status of the node pool create cloudformation be executing:

``` bash
until [[ `aws cloudformation describe-stacks --stack-name "minecraft-mix-us-west2" --query "Stacks[0].[StackStatus]" --output text` == "CREATE_COMPLETE" ]]; do  echo "The stack is NOT in a state of CREATE_COMPLETE at `date`";   sleep 30; done && echo "The Stack is built at `date` - Please proceed"
```

* Add the new Worker Node Role ARN to the ConfigMap by discovering the new node role ARN using IAM console and execute [whitelist-worker-nodes.yaml](https://github.com/yahavb/simple-game-server-eks/blob/master/specs/whitelist-worker-nodes.yaml)
* Deploy the Spot signal handler as daemon set using (spot-sig-handler-ds.yaml)[https://github.com/yahavb/simple-game-server-eks/blob/master/specs/spot-sig-handler-ds.yaml]
* Based on the node lables configured in the worker nodes provisioning set the `nodeSelector` with the proper `lifecycle` and `title` values. In out case:
``` yaml
      nodeSelector:
        lifecycle: spot
        title: minecraft
```

* Deploy the Mincraft k8s Deployment [minecraft-r1-12-deploy.yaml](https://github.com/yahavb/simple-game-server-eks/blob/master/specs/minecraft-r1-12-deploy.yaml) and discover public ip and port to conncet your Minecraft client by reading the init messages published by the game-server in the SQS queue. e.g., 
![alt text](https://github.com/yahavb/simple-game-server-eks/blob/master/images/gs_init_msg.png)
