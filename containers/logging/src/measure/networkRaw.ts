import Docker from "dockerode";

const docker = new Docker({
  socketPath: "/var/run/docker.sock",
});

export interface NetworkStats {
  rx: number;
  tx: number;
  containers: Record<
    string,
    {
      rx: number;
      tx: number;
    }
  >;
}

function sumNetworkStats(
  networks?: Record<
    string,
    {
      rx_bytes: number;
      tx_bytes: number;
    }
  >
) {
  let rx = 0;
  let tx = 0;

  for (const iface of Object.values(networks ?? {})) {
    rx += iface.rx_bytes ?? 0;
    tx += iface.tx_bytes ?? 0;
  }

  return { rx, tx };
}

async function getContainerNetworkStats(
  container: Docker.Container
): Promise<{ rx: number; tx: number }> {
  const stats = await container.stats({
    stream: false,
  });

  return sumNetworkStats(stats.networks);
}

export async function getNetworkStats(
  networkName: string
): Promise<NetworkStats> {
  const network = docker.getNetwork(networkName);

  let networkInfo: Docker.NetworkInspectInfo;

  try {
    networkInfo = await network.inspect();
  } catch {
    throw new Error(`Network not found: ${networkName}`);
  }

  const containers = networkInfo.Containers ?? {};

  const result: NetworkStats = {
    rx: 0,
    tx: 0,
    containers: {},
  };

  await Promise.all(
    Object.values(containers).map(async ({ Name, EndpointID }) => {
      if(!Name || !EndpointID){
        throw new Error(`Invalid container: Name: ${Name}; EndpointID: ${EndpointID}`)
      }
      try {
        const containerId =
          networkInfo.Containers &&
          Object.keys(networkInfo.Containers).find(
            (id) =>
              networkInfo.Containers![id]?.EndpointID === EndpointID
          );

        if (!containerId) {
          return;
        }

        const stats = await getContainerNetworkStats(
          docker.getContainer(containerId)
        );

        result.containers[Name] = stats;
        result.rx += stats.rx;
        result.tx += stats.tx;
      } catch (err) {
        console.warn(
          `Unable to read stats for ${Name}`,
          err
        );
      }
    })
  );

  return result;
}