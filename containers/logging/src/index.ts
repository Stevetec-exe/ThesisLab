import { getNetworkStats } from './measure/networkRaw.ts';
import { startInstance } from './io/operaton.ts';
import { delayMs } from './utils/time.ts';
import type { AbstractLoadTest } from './tests/abstractLoadTest.ts';
import { ConstantLoadTest } from './tests/constantLoad.ts';
import { IdleLoadTest } from './tests/idleLoad.ts';
import { CONFIG } from './config/config.ts';
import { DifferentialNetworkMeasurement } from './measure/network.ts';


async function run_tests() {
  for (let runId = 0; runId < CONFIG.tests.length; runId++) {
    const run = CONFIG.tests[runId]
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
    await runner.run();
    if (CONFIG.timing.postTestOvermeasureMs > 0) {
      console.log(`[Runner] Waiting for post-test measurement delay ${CONFIG.timing.postTestOvermeasureMs}ms`)
      await delayMs(CONFIG.timing.postTestOvermeasureMs)
    }

    const testresult = await globaltestStats.measure()
    console.log("differentials", testresult)
  }
}

async function main() {
  if (CONFIG.timing.startupDelayMs > 0) {
    console.log(`[Meta] Waiting for startup delay ${CONFIG.timing.startupDelayMs}ms`)
    await delayMs(CONFIG.timing.startupDelayMs)
  }

  for (let i = 0; i < CONFIG.repeats; i++) {
    console.info(`[Meta] Running iteration ${i + 1}/${CONFIG.repeats}`)
    await run_tests()
    if (i != CONFIG.repeats - 1) {
      if (CONFIG.timing.interRunDelayMs > 0) {
        console.log(`[Meta] Waiting for inter-run delay ${CONFIG.timing.interRunDelayMs}ms`)
        await delayMs(CONFIG.timing.interRunDelayMs)
      }
    }
  }

}
main()