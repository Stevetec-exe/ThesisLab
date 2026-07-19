const operatonUrl = process.env.OPERATON_URL ?? "http://localhost:8080/engine-rest";

export interface StartInstanceConfig {
    key: string
}

export async function startInstance(config: StartInstanceConfig) {
    const res = await fetch(`${operatonUrl}/process-definition/key/${config.key}/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    if (res.status < 200 || res.status > 299) {
        const err = await res.json()
        console.error(`[Start Instance] ${res.status}:`, err)
    }
}