/** Auto-generate a project title from source filename and date. */
export function autoProjectTitle(sourceFilename?: string): string {
  const date = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  if (sourceFilename) {
    const base = sourceFilename
      .replace(/\.[^.]+$/, "")
      .replace(/[_-]+/g, " ")
      .trim();
    if (base.length >= 2) {
      return `${base} – ${date}`;
    }
  }

  return `Dental Model – ${date}`;
}
