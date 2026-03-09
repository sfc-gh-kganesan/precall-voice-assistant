import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeSuccessBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusSuccessUi}
        fillRule="evenodd"
        d="M32 60c15.464 0 28-12.536 28-28S47.464 4 32 4 4 16.536 4 32s12.536 28 28 28m13.962-33.789a1.5 1.5 0 0 0 0-2.106l-1.992-2.02a1.5 1.5 0 0 0-2.136 0L28.929 35.178a1 1 0 0 1-1.424 0l-4.339-4.402a1.5 1.5 0 0 0-2.136 0l-1.992 2.02a1.5 1.5 0 0 0 0 2.107l7.13 7.235c.543.551 1.28.861 2.049.861s1.505-.31 2.049-.861z"
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
BadgeSuccessBadge.displayName = "BadgeSuccessBadge";
export { BadgeSuccessBadge };
