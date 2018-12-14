# simple-game-server-eks
This is an example of a dedicated game-server deployment in EKS.

We use Minecraft as the example deployed based on https://hub.docker.com/r/itzg/minecraft-server/ with a slight modification in the deployment mechanism.

The proposal herein deploys a dedicated game server as a k8s pod. Each k8s node (EC2 Instance) deployed with a public hostname and high port range is opened for client connectivity. Upon a game-server scheduling (pod scheduling), two high ports are allocated for the game-server. The clients will connect the game-server using the public hostname and port allocated. 

