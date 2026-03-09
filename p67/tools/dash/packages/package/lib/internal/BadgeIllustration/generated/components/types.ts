import { BadgeActiveBadge } from "./BadgeActiveBadge";
import { BadgeCautionBadge } from "./BadgeCautionBadge";
import { BadgeClockBadge } from "./BadgeClockBadge";
import { BadgeCriticalBadge } from "./BadgeCriticalBadge";
import { BadgeLockBadge } from "./BadgeLockBadge";
import { BadgePendingBadge } from "./BadgePendingBadge";
import { BadgePublishBadge } from "./BadgePublishBadge";
import { BadgeShieldBadge } from "./BadgeShieldBadge";
import { BadgeSuccessBadge } from "./BadgeSuccessBadge";
import { BadgeUploadBadge } from "./BadgeUploadBadge";
import { BadgeWaitBadge } from "./BadgeWaitBadge";

export type BadgeType =
  | typeof BadgeActiveBadge
  | typeof BadgeCautionBadge
  | typeof BadgeClockBadge
  | typeof BadgeCriticalBadge
  | typeof BadgeLockBadge
  | typeof BadgePendingBadge
  | typeof BadgePublishBadge
  | typeof BadgeShieldBadge
  | typeof BadgeSuccessBadge
  | typeof BadgeUploadBadge
  | typeof BadgeWaitBadge;
export interface BadgeIconProps {
  size: string;
}
