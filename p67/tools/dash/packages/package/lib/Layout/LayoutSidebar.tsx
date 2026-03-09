import * as stylex from '@stylexjs/stylex';
import type { ReactHTML } from 'react';
import {
    forwardRef,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';
import { mergeProps } from 'react-aria';
import { useMergedStyles } from '../hooks';
import { useAriaLabel } from '../internal/hooks/useLabel';
import type { Breakpoint } from '../types';
import type { ControlledComponent } from '../util/Controlled';
import { devWarning } from '../util/dev-warning';
import type { SlottedContainerProps } from '../util/SlottedContainer';
import { SlottedContainer } from '../util/SlottedContainer';
import { breakPointToMaxWidth } from './constants';
import { LayoutContext } from './LayoutContext';

type CollapseSource = 'user' | 'responsive';

type CollapseKind = 'open' | 'collapsed' | 'zerowidth';

interface CollapseContext {
    /**
     * The source of the collapse.
     */
    source: CollapseSource;
    /**
     * The kind of the collapse.
     */
    kind: CollapseKind;
}
interface LayoutSidebarBaseProps<T extends keyof ReactHTML = 'div'>
    extends SlottedContainerProps<T>,
        ControlledComponent<'collapse', boolean, CollapseContext> {
    /**
     * Whether the sidebar is collapsible.
     * @default false
     */
    collapsible?: boolean | undefined;
    /**
     * The width of the sidebar.
     */
    width?: number | string | undefined;
    /**
     * The width of the sidebar when it is collapsed.
     */
    collapsedWidth?: number | string | undefined;
    /**
     * The breakpoint at which the sidebar should collapse.
     */
    collapseBreakpoint?: Breakpoint | undefined;
    /**
     * The breakpoint at which the sidebar should be hidden.
     */
    hideBreakpoint?: Breakpoint | undefined;
    /**
     * The callback function that is called when the breakpoint is reached.
     */
    onBreakpoint?: ((reached: boolean) => void) | undefined;
    /**
     * Whether the sidebar is scrollable.
     * @default false
     */
    scrollable?: boolean | undefined;
}

interface LayoutSidebarAriaLabelProps<T extends keyof ReactHTML = 'div'>
    extends LayoutSidebarBaseProps<T> {
    /**
     * The label of the sidebar.
     */
    'aria-label': string;
}

interface LayoutSidebarAriaLabelledbyProps<T extends keyof ReactHTML = 'div'>
    extends LayoutSidebarBaseProps<T> {
    /**
     * The label of the sidebar.
     */
    'aria-labelledby': string;
}

type LayoutSidebarProps<T extends keyof ReactHTML = 'div'> =
    | LayoutSidebarAriaLabelProps<T>
    | LayoutSidebarAriaLabelledbyProps<T>;

const generateId = (() => {
    let i = 0;
    return (prefix = '') => {
        i += 1;
        return `${prefix}${i}`;
    };
})();
// export type CollapseType = "clickTrigger" | "responsive";

const styles = stylex.create({
    sidebar: {
        display: 'flex',
        flexDirection: 'column',
        flexGrow: 1,
        justifyContent: 'space-between',
    },
    sidebarContainer: {
        alignItems: 'stretch',
        display: 'flex',
        flexGrow: 0,
        flexShrink: 0,
    },
    scrollable: {
        justifyContent: 'flex-start',
        overflowY: 'auto',
    },
});
const LayoutSidebar = forwardRef<HTMLElement, LayoutSidebarProps>(
    (props, forwardedRef) => {
        const {
            width: widthProp,
            collapsedWidth = 64,
            collapseBreakpoint,
            onBreakpoint,
            defaultCollapse,
            collapse = defaultCollapse,
            onCollapseChange,
            collapsible: _collapsible,
            scrollable,
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
            ...otherProps
        } = props;

        const { addSidebar, removeSidebar } = useContext(LayoutContext);
        const [collapsed, setCollapsed] = useState(collapse);
        const [, setBelowBreakpoint] = useState(false);

        const handleSetCollapsed = useCallback(
            (value: boolean) => {
                if (!('collapsed' in props)) {
                    setCollapsed(value);
                }
                onCollapseChange?.(value, {
                    kind: 'collapsed',
                    source: 'responsive',
                });
            },
            [onCollapseChange, props],
        );

        const responsiveHandlerRef =
            useRef<
                (mediaQueryList: MediaQueryListEvent | MediaQueryList) => void
            >();

        const width = useMemo(() => {
            if (collapsed) {
                return collapsedWidth;
            }

            return widthProp || 240;
        }, [collapsed, collapsedWidth, widthProp]);

        // add current sidebar to parent context. (will cause layout shift)
        useEffect(() => {
            const uniqueId = generateId('balto-sidebar-');
            addSidebar(uniqueId);
            return () => removeSidebar(uniqueId);
        }, [addSidebar, removeSidebar]);

        //
        useEffect(() => {
            responsiveHandlerRef.current = (
                mql: MediaQueryListEvent | MediaQueryList,
            ) => {
                setBelowBreakpoint(mql.matches);
                onBreakpoint?.(mql.matches);

                if (collapsed !== mql.matches) {
                    handleSetCollapsed(mql.matches /* "responsive" */);
                }
            };
        }, [collapsed, handleSetCollapsed, onBreakpoint]);

        useEffect(() => {
            /**
             * The handler for the responsive media query.
             */
            function responsiveHandler(
                mql: MediaQueryListEvent | MediaQueryList,
            ) {
                if (responsiveHandlerRef.current) {
                    return responsiveHandlerRef.current(mql);
                }
            }
            let mql: MediaQueryList;

            if (typeof window !== 'undefined') {
                const { matchMedia } = window;
                if (
                    matchMedia &&
                    collapseBreakpoint &&
                    collapseBreakpoint in breakPointToMaxWidth
                ) {
                    mql = matchMedia(
                        `screen and (max-width: ${breakPointToMaxWidth[collapseBreakpoint]})`,
                    );
                    try {
                        mql.addEventListener('change', responsiveHandler);
                    } catch (error) {
                        devWarning(error);
                        mql.addListener(responsiveHandler);
                    }
                    responsiveHandler(mql);
                }
            }
            return () => {
                try {
                    mql?.removeEventListener('change', responsiveHandler);
                } catch (error) {
                    devWarning(error);
                    mql?.removeListener(responsiveHandler);
                }
            };
        }, [collapseBreakpoint]); // in order to accept dynamic 'breakpoint' property, we need to add 'breakpoint' into dependency array.

        const sidebarContainerStyleProps = useMergedStyles(
            '',
            { width },
            stylex.props(styles.sidebarContainer),
            // stylex.props(styles.aside, styles.dynamicWidth(width)),
        );

        const { ariaLabelProps } = useAriaLabel({
            'aria-label': ariaLabel,
            'aria-labelledby': ariaLabelledby,
        });

        return (
            <aside {...mergeProps(sidebarContainerStyleProps, ariaLabelProps)}>
                <SlottedContainer
                    {...otherProps}
                    tag="div"
                    role="presentation"
                    stylexProps={stylex.props(
                        styles.sidebar,
                        scrollable && styles.scrollable,
                    )}
                    tabIndex={scrollable ? 0 : undefined}
                    ref={forwardedRef}
                />
                {/* TODO: implement collapsible sidebar {collapsible || (below && zeroWidthTrigger) ? triggerDom : null} */}
            </aside>
        );
    },
);
LayoutSidebar.displayName = 'Layout.Sidebar';
export { LayoutSidebar };
export type { LayoutSidebarProps, CollapseContext };
