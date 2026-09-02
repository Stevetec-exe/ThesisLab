export async function delayMs(ms: number): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, ms));
}

export function now(){
  return Date.now()
}