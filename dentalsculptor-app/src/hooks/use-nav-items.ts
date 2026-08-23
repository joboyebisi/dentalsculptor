"use client";

import { useEffect, useState } from "react";
import { getNavItemsForRole, NAV_ITEMS } from "@/lib/constants";

export function useNavItems() {
  const [items, setItems] = useState(() =>
    NAV_ITEMS.filter((item) => !("researcherOnly" in item && item.researcherOnly))
  );

  useEffect(() => {
    fetch("/api/user/profile")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.user?.role) {
          setItems(getNavItemsForRole(data.user.role));
        }
      })
      .catch(() => {});
  }, []);

  return items;
}
