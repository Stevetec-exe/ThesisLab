import Docker from "dockerode";
import { promises as fs } from "fs";

const SYS = process.env.SYSPATH ?? "sys";

const docker = new Docker({
  socketPath: "/var/run/docker.sock",
});

interface CounterPaths {
  rx: string;
  tx: string;
}

const networkCounters = new Map<string, CounterPaths[]>();

async function readNumber(path: string): Promise<number> {
  return Number(await fs.readFile(path, "utf8"));
}

/**
 * Find the host-side veth interface for a container.
 */
async function findHostVeth(containerPid: number): Promise<string | undefined> {
  // This is the veth peer index from the container namespace
  const peerIndex = Number(
    await fs.readFile(
      `/proc/${containerPid}/root/sys/class/net/eth0/iflink`,
      "utf8"
    )
  );

  const interfaces = await fs.readdir(`/${SYS}/class/net`);

  for (const iface of interfaces) {
    try {
      const ifIndex = Number(
        await fs.readFile(
          `/${SYS}/class/net/${iface}/ifindex`,
          "utf8"
        )
      );

      if (ifIndex === peerIndex) {
        return iface;
      }
    } catch {
      // Interface disappeared during lookup
    }
  }

  return undefined;
}


/**
 * Run once before measuring.
 */
export async function setupNetworkStats(
  networkName: string
){

  const cacheVal = networkCounters.get(networkName)
  if(cacheVal){
    return cacheVal
  }
  const network = await docker
    .getNetwork(networkName)
    .inspect();

  const counters: CounterPaths[] = [];

  for (const containerId of Object.keys(network.Containers ?? {})) {

    const container = docker.getContainer(containerId);

    const inspect = await container.inspect();

    const pid = inspect.State.Pid;

    if (!pid) {
      continue;
    }

    const veth = await findHostVeth(pid);

    if (!veth) {
      console.warn(
        `Could not find veth for ${inspect.Name}`
      );
      continue;
    }

    counters.push({
      rx: `/${SYS}/class/net/${veth}/statistics/rx_bytes`,
      tx: `/${SYS}/class/net/${veth}/statistics/tx_bytes`,
    });
  }

  networkCounters.set(networkName, counters);
  return counters;
}


/**
 * Fast measurement function.
 */
export async function getNetworkStats(
  networkName: string
): Promise<{ rx: number; tx: number }> {

  const counters =  await setupNetworkStats(networkName)

  let rx = 0;
  let tx = 0;

  const values = await Promise.all(
    counters.flatMap((counter) => [
      readNumber(counter.rx),
      readNumber(counter.tx),
    ])
  );

  for (let i = 0; i < values.length-1; i += 2) {
    rx += values[i] || 0;
    tx += values[i + 1] || 0;
  }

  return { rx, tx };
}