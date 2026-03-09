import { forwardRef, ForwardedRef } from "react";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { BadgeIconProps } from "./types";
const BadgeShieldBadge = forwardRef(
  (props: BadgeIconProps, ref: ForwardedRef<SVGSVGElement>) => {
    const { size } = props;
    const svgContent = (
      <path
        fill={baltoTheme.statusInfoUi}
        fillRule="evenodd"
        d="M28.962 2.091C24.024 6.414 15.39 12.945 7.845 14.842c-2.143.54-3.968 2.338-3.839 4.543C5.721 48.713 25.933 63.377 31.89 63.377s26.174-14.664 27.885-43.993c.128-2.205-1.696-4.003-3.838-4.542-7.544-1.897-16.18-8.428-21.117-12.75-1.663-1.456-4.195-1.456-5.858 0m7.927 26.776a4.49 4.49 0 0 1-2.717 4.13l2.163 7.457a1.5 1.5 0 0 1-1.44 1.918l-4.923.004a1.5 1.5 0 0 1-1.442-1.916l2.145-7.435a4.494 4.494 0 0 1 1.712-8.648 4.496 4.496 0 0 1 4.502 4.49"
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
BadgeShieldBadge.displayName = "BadgeShieldBadge";
export { BadgeShieldBadge };
