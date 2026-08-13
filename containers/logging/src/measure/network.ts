import { getNetworkStats } from "./networkRaw.ts"


export type SimpleNetworkStatistics = {rx: number, tx: number}

export class DifferentialNetworkMeasurement{

    private appnet: SimpleNetworkStatistics[]
    constructor(){
        this.appnet = []
    }

    private async _measure() {
        const app = await getNetworkStats("appnet")
        this.appnet.push(app)
    }

    public async measure(): Promise<SimpleNetworkStatistics>{
        await this._measure()
        if(this.appnet.length >= 2){
            const app_curr = this.appnet[this.appnet.length-1]!
            const app_old = this.appnet[this.appnet.length-2]!
    
    
            return {
                rx: app_curr?.rx - app_old?.rx,
                tx: app_curr.tx - app_old.tx
            }
        }else{
            return {
                rx: 0,
                tx: 0
            }
        }

    }
}