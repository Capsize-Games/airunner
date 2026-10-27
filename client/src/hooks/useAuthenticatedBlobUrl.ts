import { useEffect, useState } from "react";
import { BASE_URL } from "../types/api";
import { getRequestHeaders } from "virtual:extensions";

export function useAuthenticatedBlobUrl(apiPath: string | null): string | null {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!apiPath) {
      setBlobUrl(null);
      return;
    }

    const headers = getRequestHeaders();
    const url = `${BASE_URL}${apiPath}`;

    if (Object.keys(headers).length === 0) {
      setBlobUrl(url);
      return;
    }

    let revoked = false;
    let objectUrl: string | null = null;

    fetch(url, { headers })
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (revoked) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      })
      .catch(() => {
        if (!revoked) setBlobUrl(url);
      });

    return () => {
      revoked = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [apiPath]);

  return blobUrl;
}
