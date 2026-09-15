import Docker from "dockerode";

const DOCKER = new Docker({ socketPath: "/var/run/docker.sock" });

export async function getRunningContainerNames(
  networkName = "appnet"
): Promise<string[]> {
  const network = DOCKER.getNetwork(networkName);
  const { Containers } = await network.inspect();

  const runningContainers: string[] = [];

  for (const containerInfo of Object.values(Containers??{})) {
    const container = DOCKER.getContainer(containerInfo.Name);
    const inspect = await container.inspect();

    if (inspect.State?.Running) {
      runningContainers.push(
        inspect.Name.replace(/^\//, "")
      );
    }
  }

  return runningContainers;
}