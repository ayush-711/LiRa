import { avatarColor, initials, cn } from "@/lib/utils";
import type { User } from "@/lib/types";

export function Avatar({
  user,
  size = 24,
  className,
}: {
  user: Pick<User, "name" | "avatar_url" | "email"> | null | undefined;
  size?: number;
  className?: string;
}) {
  if (!user) {
    return (
      <span
        className={cn("inline-flex items-center justify-center rounded-full bg-surface-2 text-muted", className)}
        style={{ width: size, height: size, fontSize: size * 0.42 }}
        aria-hidden
      >
        ?
      </span>
    );
  }
  if (user.avatar_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return (
      <img
        src={user.avatar_url}
        alt={user.name}
        className={cn("rounded-full object-cover", className)}
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <span
      title={user.name}
      className={cn("inline-flex items-center justify-center rounded-full font-medium text-white", className)}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.4,
        background: avatarColor(user.email || user.name),
      }}
    >
      {initials(user.name)}
    </span>
  );
}
