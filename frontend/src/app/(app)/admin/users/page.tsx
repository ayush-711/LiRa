"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { CenterSpinner } from "@/components/ui/misc";

/**
 * People management now lives on the Team page (invites, roles, activation and
 * per-person project access in one place). This route is kept so existing links
 * and bookmarks don't break.
 */
export default function AdminUsersRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/team");
  }, [router]);
  return <CenterSpinner />;
}
