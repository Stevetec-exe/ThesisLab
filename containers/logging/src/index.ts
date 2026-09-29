import { getNetworkStats } from './measure/networkRaw.ts';
import { startInstance } from './io/operaton.ts';
import { delayMs } from './utils/time.ts';
import type { AbstractLoadTest } from './tests/abstractLoadTest.ts';
import { ConstantLoadTest } from './tests/constantLoad.ts';
import { IdleLoadTest } from './tests/idleLoad.ts';
import { CONFIG } from './config/config.ts';
import { DifferentialNetworkMeasurement } from './measure/network.ts';
import { Logger } from './logging/index.ts';
import * as AMQP from './io/amqp.ts';
import { getCurrentArchitectureChannel, setCurrentArchitectureChannel } from './io/index.ts';
import { getRunningContainerNames } from './measure/containers.ts';
import { waitForNewLogfile } from './io/files.ts';
import { resetBucket } from './io/s3.ts';


async function run_tests() {
  const logger = new Logger()
  for (let runId = 0; runId < CONFIG.tests.length; runId++) {
    const run = CONFIG.tests[runId]
    const timing = { ...CONFIG.timing, ...run?.timing }
    if (!run) {
      throw new Error(`[Runner] Invalid run definition: undefined element"`)
    }
    console.info(`[Runner] Test ${runId + 1}/${CONFIG.tests.length}`)
    if (run.skip) {
      console.info(`[Runner] Test skipped.`)
      continue
    }
    const globaltestStats = new DifferentialNetworkMeasurement()
    await globaltestStats.measure()
    let runner: AbstractLoadTest;
    //console.log(net_start)
    switch (run.type) {
      case "constant":
        runner = new ConstantLoadTest(run)
        break;

      case "idle":
        runner = new IdleLoadTest(run)
        break;

      default:
        throw new Error(`Unknown run type "${run}"`)
        break;
    }

    const start_timestamp = +Date.now()
    await runner.run();
    const end_timestamp = +Date.now()
    /*if (timing.postTestOvermeasureMs > 0) {
      console.log(`[Runner] Waiting for post-test measurement delay ${timing.postTestOvermeasureMs}ms`)
      await delayMs(timing.postTestOvermeasureMs)
    }*/
    let wait_end_timestamp = end_timestamp
    if (run.type != 'idle') {
      console.log("[Runner] Waiting for service log file")
      await waitForNewLogfile("data/scratch");
      wait_end_timestamp = +Date.now()
      console.log("[Runner] Service logfile created.")
    }

    const testresult = await globaltestStats.measure()
    logger.logSync({
      testId: runId,
      config: run,
      timing: {
        start_test: start_timestamp,
        end_spawn: end_timestamp,
        end_test: wait_end_timestamp
      },
      net_total: testresult
    })
    console.log("differentials", testresult)
    if (getCurrentArchitectureChannel() == 's3') {
      console.log("[S3] Resetting context bucket")
      await resetBucket()
    }
    await delayMs(timing.interTestDelayMs)
  }
  await logger.save(getCurrentArchitectureChannel())
}

async function main() {
  if (CONFIG.timing.startupDelayMs > 0) {
    console.log(`[Meta] Waiting for startup delay ${CONFIG.timing.startupDelayMs}ms`)
    await delayMs(CONFIG.timing.startupDelayMs)
  }

  let i = 0
  while (i < CONFIG.repeats || CONFIG.repeats < 0) {
    if (CONFIG.repeats < 0) {
      console.info(`[Meta] Running iteration ${i + 1} / ∞`)
    } else {
      console.info(`[Meta] Running iteration ${i + 1}/${CONFIG.repeats}`)
    }
    i++
    await run_tests()
    if (i != CONFIG.repeats - 1) {
      if (CONFIG.timing.interRunDelayMs > 0) {
        console.log(`[Meta] Waiting for inter-run delay ${CONFIG.timing.interRunDelayMs}ms`)
        await delayMs(CONFIG.timing.interRunDelayMs)
      }
    }
  }

}

//main()

async function main2() {
  let colocated = await getRunningContainerNames();
  const this_container = colocated.find(n => n.includes('logging'));
  if (!this_container) {
    console.log("[Container Discovery] No logging container found - this should never happen...")
    return
  }
  const prefix = this_container.split('logging')[0]
  colocated = colocated.map(n => n.slice(prefix?.length).slice(0, -2))
  let dummy_services = colocated.filter(c => c.includes('-service'))
  dummy_services = dummy_services.map(s => s.split('-service')[0] ?? '').filter(Boolean)
  const target_service = dummy_services[0]!
  if (dummy_services.length != 1) {
    console.log(`[Container Discovery] Multiple sink services found: ${dummy_services}`)
    return
  }

  const derivedChannel = {
    'push': 'push',
    'poll': 'poll',
    'broker': 'amqp',
    'storage': 's3'
  }[target_service] as Parameters<typeof setCurrentArchitectureChannel>[0]
  if (!derivedChannel) {
    console.log(`[Container Discovery] Invalid sink service '${target_service}'`)
    return
  }

  console.log(`[Container Discovery] Detected valid dummy service for architecture '${target_service}'`)

  setCurrentArchitectureChannel(derivedChannel);
  await AMQP.init();
  await main();
  await AMQP.close()
}

main2()
