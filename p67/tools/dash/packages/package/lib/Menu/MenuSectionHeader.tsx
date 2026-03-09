import { baltoTheme } from '@snowflake/balto-themes/baltoTheme.stylex.js';
import { tokens } from '@snowflake/stellar-tokens/tokens.stylex';
import * as stylex from '@stylexjs/stylex';
import { forwardRef, useContext } from 'react';
import { Header } from 'react-aria-components';

import { useMergedStyles } from '../hooks';
import { useTypeRamp } from '../internal/hooks/useTypeRamp';
import { SizeContext } from '../main';

const styles = stylex.create({
    header: {
        color: baltoTheme.reusableTextSecondary,
        padding: `${tokens['space-vertical-2xs']} ${tokens['space-horizontal-md']}`,
    },
    smallHeader: {
        padding: `${tokens['space-vertical-3xs']} ${tokens['space-horizontal-sm']}`,
    },
});

type MenuSectionHeaderProps = React.HTMLAttributes<HTMLElement>;

const MenuSectionHeader = forwardRef<HTMLDivElement, MenuSectionHeaderProps>(
    function MenuSectionHeader(props, forwardedRef) {
        const sizeContext = useContext(SizeContext);
        const { className, style, ...otherProps } = props;
        const textStyles = useTypeRamp(
            sizeContext === 'small' ? 'labelSmall' : 'smallSingleLineBold',
        );

        return (
            <Header
                {...otherProps}
                ref={forwardedRef}
                {...useMergedStyles(
                    className,
                    style,
                    stylex.props(styles.header, textStyles),
                )}
            />
        );
    },
);

MenuSectionHeader.displayName = 'Menu.SectionHeader';

export type { MenuSectionHeaderProps };
export { MenuSectionHeader };
