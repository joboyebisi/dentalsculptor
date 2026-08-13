/** Lightweight UI feedback sounds (no external files). Pascal-style micro-interactions. */

export type SfxEvent = "tool-click" | "select" | "export-done" | "toggle";

let audioCtx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    try {
      audioCtx = new AudioContext();
    } catch {
      return null;
    }
  }
  return audioCtx;
}

function tone(freq: number, duration: number, gain = 0.04) {
  const ctx = getCtx();
  if (!ctx) return;
  if (ctx.state === "suspended") void ctx.resume();

  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = "sine";
  osc.frequency.value = freq;
  amp.gain.value = gain;
  osc.connect(amp);
  amp.connect(ctx.destination);
  osc.start();
  amp.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
  osc.stop(ctx.currentTime + duration);
}

export function triggerSFX(event: SfxEvent) {
  switch (event) {
    case "tool-click":
      tone(520, 0.06, 0.035);
      break;
    case "select":
      tone(660, 0.05, 0.03);
      tone(880, 0.04, 0.02);
      break;
    case "toggle":
      tone(480, 0.04, 0.025);
      break;
    case "export-done":
      tone(523, 0.08, 0.03);
      tone(659, 0.1, 0.025);
      break;
  }
}
