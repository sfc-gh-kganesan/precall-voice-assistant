import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeLockBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusNeutralUi}
        fillRule="evenodd"
        d="M57 29c0-5.523-4.477-10-10-10v-3.5C47 6.94 40.06 0 31.5 0S16 6.94 16 15.5v3.55c-5.053.501-9 4.765-9 9.95v25c0 5.523 4.477 10 10 10h30c5.523 0 10-4.477 10-10zM42 15.5V19H21v-3.5C21 9.701 25.701 5 31.5 5S42 9.701 42 15.5m-5.501 21.49a4.49 4.49 0 0 1-2.717 4.13l2.162 7.458a1.5 1.5 0 0 1-1.44 1.917l-4.922.004a1.5 1.5 0 0 1-1.443-1.916l2.145-7.435a4.495 4.495 0 0 1-2.784-4.152 4.496 4.496 0 0 1 4.496-4.496 4.496 4.496 0 0 1 4.503 4.49"
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
BadgeLockBadge.displayName = "BadgeLockBadge";
export { BadgeLockBadge };
