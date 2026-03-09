import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgePublishBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusInfoUi}
        fillRule="evenodd"
        d="M32 60c15.464 0 28-12.536 28-28S47.464 4 32 4 4 16.536 4 32s12.536 28 28 28m2.406-41.217a2.724 2.724 0 0 0-3.823 0l-12.869 12.69a1 1 0 0 0-.008 1.416l2.414 2.433a1 1 0 0 0 1.412.008l8.246-8.13.002 17.8a1 1 0 0 0 1 1h3.436a1 1 0 0 0 1-1L35.213 27.2l8.255 8.14a1 1 0 0 0 1.412-.008l2.414-2.433a1 1 0 0 0-.008-1.417z"
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
BadgePublishBadge.displayName = "BadgePublishBadge";
export { BadgePublishBadge };
