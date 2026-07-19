import type { ConstantLoadTestConfig } from "../tests/constantLoad.ts"
import type { IdleLoadTestConfig } from "../tests/idleLoad.ts"

export type SourceConfig = {
    tests: TestConfig[],

    networks:{
        appnet: string
        refnet: string
    },

    timing:{
        /** Delay from startup of container before beginning to measure */
        startupDelayMs: number
        /** Delay between different tests */
        interTestDelayMs: number
        /** Delay between repetitions of the full test-set */
        interRunDelayMs: number,

        /** Time before the final measurement is taken after end of test. use this if you want to count trailing packets*/
        postTestOvermeasureMs: number
    }

    /** Numer of times the entire test-set is repeated */
    repeats: number
}

type TestConfig = ({
    type: "constant"
} & ConstantLoadTestConfig) | ({
    type: "idle"
} & IdleLoadTestConfig)