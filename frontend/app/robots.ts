import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

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
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
