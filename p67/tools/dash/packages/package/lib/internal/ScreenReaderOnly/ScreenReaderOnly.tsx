import * as stylex from '@stylexjs/stylex';

const styles = stylex.create({
    srOnly: {
        borderWidth: 0,
        clip: 'rect(0 0 0 0)',
        height: '1px',
        margin: '-1px',
        overflow: 'hidden',
        padding: 0,
        position: 'absolute',
    },
});

/**
 * The component that renders a screen reader only element.
 */
export function ScreenReaderOnly({
    children,
}: {
    /**
     * The children of the screen reader only element.
     */
    children: React.ReactNode;
}) {
    return <span {...stylex.props(styles.srOnly)}>{children}</span>;
}
