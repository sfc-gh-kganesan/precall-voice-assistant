import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeCriticalBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusCriticalUi}
        fillRule="evenodd"
        d="M32 60c15.464 0 28-12.536 28-28S47.464 4 32 4 4 16.536 4 32s12.536 28 28 28m9.551-16.62c-.56.56-1.468.56-2.028 0l-6.509-6.51a1.434 1.434 0 0 0-2.028 0l-6.509 6.51c-.56.56-1.468.56-2.028 0l-2.029-2.03a1.435 1.435 0 0 1 0-2.028l6.508-6.509c.56-.56.56-1.468 0-2.028l-6.307-6.308a1.434 1.434 0 0 1 0-2.028l2.029-2.029c.56-.56 1.468-.56 2.028 0l6.308 6.308c.56.56 1.468.56 2.028 0l6.308-6.308c.56-.56 1.468-.56 2.028 0l2.03 2.029c.56.56.56 1.468 0 2.028l-6.308 6.308c-.56.56-.56 1.468 0 2.028l6.508 6.509c.56.56.56 1.468 0 2.028z"
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
BadgeCriticalBadge.displayName = "BadgeCriticalBadge";
export { BadgeCriticalBadge };
