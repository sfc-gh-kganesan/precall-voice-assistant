import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeCautionBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusCautionUi}
        fillRule="evenodd"
        d="M4.859 48.414 24.93 8.424c2.969-5.914 11.448-5.895 14.39.034l19.837 39.99C61.798 53.767 57.912 60 51.955 60h-39.91c-5.973 0-9.858-6.263-7.186-11.586m23.668-27.388a1 1 0 0 1 1-1.026h4.946a1 1 0 0 1 1 1.026l-.447 17a1 1 0 0 1-1 .974h-4.052a1 1 0 0 1-1-.974zM35.5 46.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0"
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
BadgeCautionBadge.displayName = "BadgeCautionBadge";
export { BadgeCautionBadge };
