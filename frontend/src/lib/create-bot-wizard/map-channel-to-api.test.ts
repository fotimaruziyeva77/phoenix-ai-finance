import { describe, expect, it } from "vitest";

import { mapChannelToInitialChannel } from "./map-channel-to-api";

describe("mapChannelToInitialChannel", () => {
  it("maps wizard ids to API initial_channel", () => {
    expect(mapChannelToInitialChannel("website_widget")).toBe("web");
    expect(mapChannelToInitialChannel("telegram")).toBe("telegram");
    expect(mapChannelToInitialChannel("both")).toBe("both");
    expect(mapChannelToInitialChannel(null)).toBeNull();
  });
});
