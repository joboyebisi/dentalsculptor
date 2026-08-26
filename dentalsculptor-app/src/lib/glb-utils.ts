/** Validate GLB magic header before upload or parse. */
export function isValidGlbBuffer(buffer: ArrayBuffer | Buffer | Uint8Array): boolean {
  const view = buffer instanceof Buffer ? buffer : new Uint8Array(buffer);
  if (view.byteLength < 12) return false;
  const magic = String.fromCharCode(view[0]!, view[1]!, view[2]!, view[3]!);
  return magic === "glTF";
}

export function glbValidationError(buffer: ArrayBuffer | Buffer | Uint8Array): string {
  const view = buffer instanceof Buffer ? buffer : new Uint8Array(buffer);
  if (view.byteLength < 12) {
    return `GLB file is too small (${view.byteLength} bytes). The edit worker may have failed.`;
  }
  const magic = String.fromCharCode(view[0]!, view[1]!, view[2]!, view[3]!);
  const preview = String.fromCharCode(...view.subarray(0, Math.min(16, view.byteLength)));
  if (magic !== "glTF") {
    return `Invalid GLB header (expected "glTF", got "${preview.replace(/[^\x20-\x7E]/g, "?")}"). The stored file may be an error page or corrupt export.`;
  }
  return "Invalid GLB file.";
}
