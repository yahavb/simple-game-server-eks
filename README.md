# simple-game-server-eks

This is an example of a dedicated game-server deployment in EKS. The goal is to provide a robust and straightforward game-server deployment pattern on k8s. 

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
