import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeActiveBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusNeutralUi}
        fillRule="evenodd"
        d="M32 60c15.464 0 28-12.536 28-28S47.464 4 32 4 4 16.536 4 32s12.536 28 28 28m-1.83-41.881Q31.07 18 32.002 18c7.732 0 14 6.268 14 14s-6.268 14-14 14q-.933 0-1.832-.118l-.603 4.627q1.197.157 2.435.158c10.309 0 18.666-8.358 18.666-18.667s-8.357-18.667-18.666-18.667q-1.238.001-2.435.158zm-6.69 2.772a14 14 0 0 1 3.163-1.83l-1.787-4.31a18.7 18.7 0 0 0-4.22 2.44zm-4.417 5.75a14 14 0 0 1 1.83-3.163l-3.7-2.843a18.7 18.7 0 0 0-2.44 4.219zM18.002 32q0-.933.118-1.831l-4.627-.604a18.8 18.8 0 0 0 0 4.87l4.627-.604A14 14 0 0 1 18.002 32m2.891 8.522a14 14 0 0 1-1.83-3.164l-4.31 1.788a18.7 18.7 0 0 0 2.44 4.22zm5.75 4.417a14 14 0 0 1-3.163-1.83l-2.843 3.7c1.283.986 2.7 1.81 4.219 2.44z"
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
BadgeActiveBadge.displayName = "BadgeActiveBadge";
export { BadgeActiveBadge };
