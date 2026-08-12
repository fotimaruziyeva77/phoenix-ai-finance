import type { ChannelChoiceId } from "./types";

/** Maps wizard channel card id to POST /api/v1/bots `initial_channel`. */
export function mapChannelToInitialChannel(
  id: ChannelChoiceId | null,
): "web" | "telegram" | "both" | null {
  if (id === "website_widget") return "web";
  if (id === "telegram") return "telegram";
  if (id === "both") return "both";
  return null;
}
