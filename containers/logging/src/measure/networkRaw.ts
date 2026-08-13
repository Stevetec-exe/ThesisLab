import Docker from "dockerode";

const DOCKER = new Docker({socketPath: '/var/run/docker.sock'});

type NetworkStats = {
  rx: number;
  tx: number;
};

/**
 * Get aggregate network traffic for all containers attached to this Docker network.
 *
 * Returned values are from the containers' perspective:
 *   rx = bytes received by containers
 *   tx = bytes transmitted by containers
 */
export async function getNetworkStats(
  networkName: string
): Promise<NetworkStats> {
  const network = DOCKER.getNetwork(networkName);
  const networkInfo = await network.inspect();

  const containerIds = Object.keys(networkInfo.Containers ?? {});

  const stats = await Promise.all(
    containerIds.map(async (containerId) => {
      const container = DOCKER.getContainer(containerId);

      // stream=false returns a single Stats object.
      const data = await container.stats({ stream: false });

      const networkStats = Object.values(data.networks ?? {}).reduce(
        (total, network) => ({
          rx: total.rx + network.rx_bytes,
          tx: total.tx + network.tx_bytes,
        }),
        { rx: 0, tx: 0 }
      );

      return networkStats;
    })
  );

  return stats.reduce(
    (total, current) => ({
      rx: total.rx + current.rx,
      tx: total.tx + current.tx,
    }),
    { rx: 0, tx: 0 }
  );
}