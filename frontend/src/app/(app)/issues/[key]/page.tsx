"use client";

import { useParams } from "next/navigation";
import { IssueDetailView } from "@/components/issue/IssueDetailView";

export default function IssuePage() {
  const { key } = useParams<{ key: string }>();
  return (
    <div className="mx-auto max-w-5xl">
      <IssueDetailView issueKey={key} />
    </div>
  );
}
