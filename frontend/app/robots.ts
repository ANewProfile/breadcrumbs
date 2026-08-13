import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Only reachable when signed in, and carries no content worth indexing.
        disallow: ["/settings"],
      },
    ],
  };
}
