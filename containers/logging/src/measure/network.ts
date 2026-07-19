import { CONFIG } from "../config/config.ts"
import { getNetworkStats, type NetworkStats } from "./networkRaw.ts"

export type GlobalNetworkStats = {
    rx: number
    tx: number
}

export class DifferentialNetworkMeasurement{

    private appnet: NetworkStats[]
    private refnet: NetworkStats[]
    constructor(){
        this.appnet = []
        this.refnet = []
    }

    private async _measure() {
        const app = await getNetworkStats(CONFIG.networks.appnet)
        const ref = await getNetworkStats(CONFIG.networks.refnet)
        this.appnet.push(app)
        this.refnet.push(ref)
    }

    public async measure(): Promise<GlobalNetworkStats>{
        await this._measure()
        if(this.appnet.length >= 2){
            const app_curr = this.appnet[this.appnet.length-1]!
            const app_old = this.appnet[this.appnet.length-2]!
    
            const ref_curr = this.refnet[this.refnet.length-1]!
            const ref_old = this.refnet[this.refnet.length-2]!
    
            const app_delta = {
                rx: app_curr?.rx - app_old?.rx,
                tx: app_curr.tx - app_old.tx
            }

            const ref_delta = {
                rx: ref_curr?.rx - ref_old?.rx,
                tx: ref_curr.tx - ref_old.tx
            }

            return {
                rx: app_delta.rx - ref_delta.rx,
                tx: app_delta.tx - ref_delta.tx
            }
        }else{
            return {
                rx: 0,
                tx: 0
            }
        }

    }
}