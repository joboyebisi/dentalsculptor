/** Polyfill browser globals for Three.js loaders in Node.js API routes. */
if (typeof globalThis.self === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).self = globalThis;
}
