import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeClockBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusNeutralUi}
        fillRule="evenodd"
        d="M60 32c0 15.464-12.536 28-28 28S4 47.464 4 32 16.536 4 32 4s28 12.536 28 28M29.25 16a2 2 0 0 0-2 2v17.75a2 2 0 0 0 2 2H44.5a2 2 0 0 0 2-2v-1.5a2 2 0 0 0-2-2H33.75a1 1 0 0 1-1-1V18a2 2 0 0 0-2-2z"
        clipRule="evenodd"
      />
    );
    return (
      <svg
        style={{ width: size, height: size }}
        viewBox="0 0 64 64"
        role="presentation"
        fill="none"
        stroke="none"
        xmlns="http://www.w3.org/2000/svg"
        ref={ref}
        {...props}
      >
        {svgContent}
      </svg>
    );
  },
);
BadgeClockBadge.displayName = "BadgeClockBadge";
export { BadgeClockBadge };
