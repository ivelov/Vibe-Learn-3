"use client";

import { useEffect, useState } from "react";

/**
 * Returns true only after the component has mounted on the client. Used to
 * defer rendering of window-dependent chart libraries (Recharts) so the static
 * export build and hydration don't choke on a missing DOM.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted;
}
