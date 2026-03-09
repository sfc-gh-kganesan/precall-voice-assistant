import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeUploadBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusNeutralUi}
        d="M11.429 53.666q.383 0 .758-.025v.025h16.711V37.173l-5.783 5.783a1 1 0 0 1-1.414 0l-2.393-2.392a1 1 0 0 1 0-1.414l11.573-11.573a1 1 0 0 1 1.414 0L43.868 39.15a1 1 0 0 1 0 1.414l-2.393 2.392a1 1 0 0 1-1.414 0l-5.78-5.78v16.49h12.954v-.018q.381.018.765.018c8.837 0 16-7.163 16-16s-7.163-16-16-16q-.585 0-1.159.041C43.748 15.367 37.241 11 29.711 11c-10.519 0-19.047 8.528-19.047 19.048q0 .394.016.785C4.717 31.218 0 36.177 0 42.237c0 6.312 5.117 11.429 11.429 11.429"
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
BadgeUploadBadge.displayName = "BadgeUploadBadge";
export { BadgeUploadBadge };
