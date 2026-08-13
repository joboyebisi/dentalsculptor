/** fal.ai Hunyuan generation mode from environment. */
export function getFalGenerationOptions(): {
  enable_geometry: boolean;
  enable_pbr: boolean;
  mode: "pbr" | "geometry";
} {
  const geometryOnly = process.env.FAL_ENABLE_GEOMETRY === "true";
  const enablePbr = !geometryOnly && process.env.FAL_ENABLE_PBR !== "false";

  return {
    enable_geometry: geometryOnly,
    enable_pbr: enablePbr,
    mode: geometryOnly ? "geometry" : "pbr",
  };
}
